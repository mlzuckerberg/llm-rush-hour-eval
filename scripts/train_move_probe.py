#!/usr/bin/env python3
"""
Train a supervised next-move probe from oracle trajectories.

The probe is evaluated with next-move accuracy, legality, and rollout behavior.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.board import Board
from game.solver_bfs import bfs_solution_moves


@dataclass
class StateExample:
    board: str
    move: str
    level_id: str


# load levels
def _load_levels(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "levels" in raw:
        return list(raw["levels"])
    if isinstance(raw, list):
        return raw
    raise ValueError(f"bad levels JSON shape: {path}")


# move to str
def _move_to_str(letter: str, steps: int) -> str:
    sign = "+" if steps > 0 else ""
    return f"{letter}{sign}{steps}"


# str to move
def _str_to_move(move: str) -> tuple[str, int]:
    letter = move[0]
    steps = int(move[1:])
    return letter, steps


# build oracle examples
def _build_oracle_examples(level_rows: list[dict[str, Any]]) -> list[StateExample]:
    examples: list[StateExample] = []
    for row in level_rows:
        rid = row.get("id", row["board"][:8])
        board = Board.from_fogleman_string(row["board"])
        sol = bfs_solution_moves(board, forbid_consecutive_same_piece=True)
        if not sol:
            continue
        b = board.copy()
        for idx, steps in sol:
            board_state = b.board_string()
            letter = b.labels[idx]
            examples.append(StateExample(board=board_state, move=_move_to_str(letter, steps), level_id=rid))
            b.apply_move(idx, steps)
    return examples


# split by level
def _split_by_level(rows: list[dict[str, Any]], train_frac: float, seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    rows_copy = list(rows)
    rng.shuffle(rows_copy)
    n_train = max(1, int(len(rows_copy) * train_frac))
    n_train = min(n_train, len(rows_copy) - 1) if len(rows_copy) > 1 else 1
    return rows_copy[:n_train], rows_copy[n_train:]


# legal move strings
def _legal_move_strings(board: Board) -> set[str]:
    legal = set()
    for idx, steps in board.list_moves():
        legal.add(_move_to_str(board.labels[idx], steps))
    return legal


# rollout probe on levels
def _rollout_probe_on_levels(
    model: Any,
    vectorizer: Any,
    levels: list[dict[str, Any]],
    max_steps: int,
) -> dict[str, Any]:
    per_level: list[dict[str, Any]] = []
    for row in levels:
        rid = row.get("id", row["board"][:8])
        b = Board.from_fogleman_string(row["board"])
        applied = 0
        won = False
        for step in range(max_steps):
            if b.is_solved():
                won = True
                break
            pred = model.predict(vectorizer.transform([b.board_string()]))[0]
            legal = _legal_move_strings(b)
            if pred not in legal:
                break
            letter, steps = _str_to_move(pred)
            b.apply_move(b.label_to_index(letter), steps)
            applied += 1
        if b.is_solved():
            won = True
        per_level.append({"id": rid, "won": won, "applied_moves": applied})
    wins = sum(1 for r in per_level if r["won"])
    mean_applied = sum(r["applied_moves"] for r in per_level) / len(per_level) if per_level else 0.0
    return {
        "levels": len(per_level),
        "wins": wins,
        "win_rate": (wins / len(per_level)) if per_level else 0.0,
        "mean_applied_moves": mean_applied,
        "per_level": per_level,
    }


# main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", type=Path, default=ROOT / "data" / "levels_eval.json")
    ap.add_argument("--train-frac", type=float, default=0.8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-steps", type=int, default=200)
    ap.add_argument(
        "--out",
        type=Path,
        default=ROOT / "evaluation_outputs" / "trained_probe_summary.json",
    )
    args = ap.parse_args()

    # local import so core repo remains usable without sklearn unless this script is run
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    levels = _load_levels(args.levels)
    train_levels, test_levels = _split_by_level(levels, args.train_frac, args.seed)
    train_examples = _build_oracle_examples(train_levels)
    test_examples = _build_oracle_examples(test_levels)
    if not train_examples or not test_examples:
        raise SystemExit("not enough examples; adjust train fraction or dataset")

    x_train = [e.board for e in train_examples]
    y_train = [e.move for e in train_examples]
    x_test = [e.board for e in test_examples]
    y_test = [e.move for e in test_examples]

    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 3), lowercase=False)
    xtr = vectorizer.fit_transform(x_train)
    xte = vectorizer.transform(x_test)
    clf = LogisticRegression(max_iter=2000)
    clf.fit(xtr, y_train)

    preds = clf.predict(xte)
    acc = sum(1 for p, y in zip(preds, y_test) if p == y) / len(y_test)

    legal_hits = 0
    for ex, pred in zip(test_examples, preds):
        b = Board.from_fogleman_string(ex.board)
        if pred in _legal_move_strings(b):
            legal_hits += 1
    legal_rate = legal_hits / len(test_examples)

    rollout = _rollout_probe_on_levels(clf, vectorizer, test_levels, args.max_steps)
    summary: dict[str, Any] = {
        "model_type": "trained_next_move_probe",
        "features": "tfidf_char_1_3",
        "classifier": "logistic_regression_multinomial",
        "train_levels": len(train_levels),
        "test_levels": len(test_levels),
        "train_examples": len(train_examples),
        "test_examples": len(test_examples),
        "next_move_accuracy": acc,
        "next_move_legal_rate": legal_rate,
        "rollout_eval": rollout,
        "seed": args.seed,
        "max_steps": args.max_steps,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
