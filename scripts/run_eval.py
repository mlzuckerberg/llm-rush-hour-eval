#!/usr/bin/env python3
"""
Protocol A — evaluate planners on a JSON level list (single API call per level for LLMs).

Supports oracle (BFS plan), random rollout, and OpenAI full-plan completion.
Writes one JSON with ``per_level`` rows (``applied``, ``plan_len_parsed``, etc.).

Examples:
  PYTHONPATH=. python scripts/run_eval.py --planner oracle --levels data/sample_levels.json
  PYTHONPATH=. python scripts/run_eval.py --planner random --levels data/sample_levels.json --seed 1
  PYTHONPATH=. python scripts/run_eval.py --planner openai --levels data/sample_levels.json --config config.yaml --max-levels 5 --sleep-between-levels 1.0

Requires ``OPENAI_API_KEY`` in environment for OpenAI planner runs (see README).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.baseline import random_rollout  # noqa: E402
from game.board import Board  # noqa: E402
from game.simulator import moves_from_indices, run_plan  # noqa: E402
from game.solver_bfs import bfs_solution_moves  # noqa: E402
from llm.client import LLMConfig, chat_text, load_llm_config  # noqa: E402
from llm.parse_output import parse_plan  # noqa: E402
from llm.prompt_builder import build_full_plan_prompt  # noqa: E402


# load levels file
def _load_levels_file(path: Path) -> tuple[List[Dict[str, Any]], Dict[str, Any] | None]:
    """Load ``levels`` list and optional ``meta`` from ``{levels, meta}`` or a bare list."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "levels" in raw:
        return raw["levels"], raw.get("meta")  # type: ignore[return-value]
    if isinstance(raw, list):
        return raw, None
    raise ValueError(f"Unexpected JSON shape in {path}")


# few shot path
def _few_shot_path(k: int) -> Path | None:
    if k == 0:
        return None
    if k in (1, 2):
        return ROOT / "prompts" / f"examples_fewshot_{k}.txt"
    raise ValueError("few_shot must be 0, 1, or 2")


# oracle letter moves
def _oracle_letter_moves(board: Board) -> list[tuple[str, int]]:
    sol = bfs_solution_moves(board, True)
    if sol is None:
        return []
    return moves_from_indices(board, sol)


# main
def main() -> None:
    """CLI entry: run all planners and emit summary JSON to ``--out``."""
    # oracle / random = free; openai = one completion per level (protocol a)
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", type=Path, default=ROOT / "data" / "sample_levels.json")
    ap.add_argument("--planner", choices=("oracle", "random", "openai"), required=True)
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument(
        "--max-levels",
        type=int,
        default=10_000,
        help="Cap number of levels from the JSON (default: run all levels in the file).",
    )
    ap.add_argument(
        "--sleep-between-levels",
        type=float,
        default=0.0,
        help="Seconds to wait after each API call (openai only). Reduces burst rate.",
    )
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, default=ROOT / "evaluation_outputs" / "last_run.json")
    ap.add_argument(
        "--debug",
        action="store_true",
        help="For openai: include raw model text (truncated) in JSON for debugging.",
    )
    ap.add_argument(
        "--few-shot",
        type=int,
        choices=(0, 1, 2),
        default=0,
        help="0=no few-shot; 1 or 2=toy solved examples in prompts/examples_fewshot_{1,2}.txt",
    )
    args = ap.parse_args()

    rows, levels_meta = _load_levels_file(args.levels)
    rows = rows[: args.max_levels]
    rng = random.Random(args.seed)

    rules_path = ROOT / "prompts" / "rules.txt"
    examples_path = _few_shot_path(args.few_shot)
    cfg_path = args.config
    llm_cfg = load_llm_config(cfg_path)
    if args.planner == "openai":
        llm_cfg = LLMConfig("openai", llm_cfg.model)

    results: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        board = Board.from_fogleman_string(row["board"])
        rid = row.get("id", row["board"][:8])
        opt = row.get("optimal_moves")

        # symbolic planners (no api)
        if args.planner == "oracle":
            moves = _oracle_letter_moves(board)
            pr = run_plan(board, moves)
            results.append(
                {
                    "id": rid,
                    "planner": "oracle",
                    "few_shot": args.few_shot,
                    "won": pr.won,
                    "applied": pr.num_applied,
                    "illegal_at": pr.first_illegal_index,
                    "plan_len": len(moves),
                    "optimal_moves": opt,
                }
            )
        elif args.planner == "random":
            rr = random_rollout(board, rng, max_moves=8000)
            results.append(
                {
                    "id": rid,
                    "planner": "random",
                    "few_shot": args.few_shot,
                    "won": rr.won,
                    "moves_tried": rr.num_moves,
                    "optimal_moves": opt,
                }
            )
        else:
            # llm: full plan in one shot → parse → simulate prefix until illegal/win
            user = build_full_plan_prompt(board, rules_path, examples_path)
            nlv = len(rows)
            print(f"[{i + 1}/{nlv}] {rid} (opt={opt}) — calling API...", flush=True)
            text = chat_text(
                "You solve Rush Hour puzzles. Output only move lines; no explanation.",
                user,
                llm_cfg,
            )
            moves = parse_plan(text)
            pr = run_plan(board, moves)
            row_out: dict[str, Any] = {
                "id": rid,
                "planner": args.planner,
                "few_shot": args.few_shot,
                "won": pr.won,
                "applied": pr.num_applied,
                "illegal_at": pr.first_illegal_index,
                "plan_len_parsed": len(moves),
                "optimal_moves": opt,
                "raw_chars": len(text),
            }
            if args.debug:
                row_out["raw_preview"] = text[:8000]  # cap json size in normal runs
                row_out["parsed_preview"] = moves[:30]
                lm = board.list_moves()
                row_out["legal_moves_preview"] = [(board.labels[i], s) for i, s in lm[:30]]
            results.append(row_out)
            print(
                f"    → won={row_out['won']} applied={row_out['applied']} "
                f"parsed_lines={row_out['plan_len_parsed']} raw_chars={row_out['raw_chars']}",
                flush=True,
            )
            if args.sleep_between_levels > 0 and i + 1 < len(rows):
                time.sleep(args.sleep_between_levels)

    wins = sum(1 for r in results if r.get("won"))
    summary: dict[str, Any] = {
        "levels": len(results),
        "wins": wins,
        "win_rate": wins / len(results) if results else 0.0,
        "planner": args.planner,
        "few_shot": args.few_shot,
        "seed": args.seed,
        "per_level": results,
    }
    if levels_meta is not None:
        summary["levels_file_meta"] = levels_meta
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_level"}, indent=2))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
