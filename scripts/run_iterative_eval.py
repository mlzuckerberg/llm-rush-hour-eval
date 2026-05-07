#!/usr/bin/env python3
"""
Iterative LLM eval: one API call per step, re-prompting with the updated board.

This matches the proposal's "hint-following trajectory" style evaluation and
usually improves win rate vs single-shot full-plan generation.

Usage:
  PYTHONPATH=. python scripts/run_iterative_eval.py --planner openai --config config.yaml \\
      --levels data/levels_eval.json --max-steps 500 \\
      --out evaluation_outputs/openai_iterative.json

Self-consistency (k>1): each step samples the same prompt k times, scores each
parsed plan by how many moves are legal in sequence from the **current** board,
picks the sample with the **longest legal prefix**, then applies **only that
sample's first move**. This is not search — it is voting over independent samples.

--retry-on-illegal: if the chosen first move is still illegal (or all k samples
score 0 legal prefix), one extra API call is made on the **same** board with a
short correction line (still not search; no tree expansion).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.board import Board  # noqa: E402
from game.simulator import run_plan  # noqa: E402
from llm.client import LLMConfig, chat_text, load_llm_config  # noqa: E402
from llm.parse_output import parse_plan  # noqa: E402
from llm.prompt_builder import build_one_move_prompt  # noqa: E402

_SYSTEM_ONE_MOVE = "You output exactly one Rush Hour move line when asked."

_RETRY_USER_SUFFIX = (
    "\n\n---\nThe simulator rejected your last answer (illegal or empty). "
    "The board is unchanged. Output exactly one **legal** next move as a single "
    "line: LETTER STEPS (same format as the rules)."
)


# few shot path
def _few_shot_path(k: int) -> Path | None:
    if k == 0:
        return None
    if k in (1, 2):
        return ROOT / "prompts" / f"examples_fewshot_{k}.txt"
    raise ValueError("few_shot must be 0, 1, or 2")


# load levels file
def _load_levels_file(path: Path) -> tuple[List[Dict[str, Any]], Dict[str, Any] | None]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "levels" in raw:
        return raw["levels"], raw.get("meta")
    if isinstance(raw, list):
        return raw, None
    raise ValueError(f"Unexpected JSON shape in {path}")


# legal prefix length
def _legal_prefix_length(board: Board, moves: List[Tuple[str, int]]) -> int:
    """How many moves from `moves` apply legally in order from `board` (stops at first illegal)."""
    if not moves:
        return 0
    pr = run_plan(board, moves)
    return int(pr.num_applied)


# choose first move self consistency
def _choose_first_move_self_consistency(
    board: Board,
    llm_cfg: LLMConfig,
    user_prompt: str,
    k: int,
    sleep_s: float,
) -> tuple[Tuple[str, int] | None, int, List[int]]:
    """
    k independent completions; score each by legal prefix length of full parsed plan.
    Return (first_move of best sample or None, api_calls_used, list of k prefix lengths).

    Only considers samples with **legal prefix length >= 1** (so the first parsed move is legal).
    """
    api = 0
    best_len = 0
    best_first: Tuple[str, int] | None = None
    lengths: list[int] = []

    # longest legal-prefix wins; if two tie in length, first sample in draw order wins
    for _ in range(k):
        text = chat_text(_SYSTEM_ONE_MOVE, user_prompt, llm_cfg)
        api += 1
        moves = parse_plan(text)
        ln = _legal_prefix_length(board, moves)
        lengths.append(ln)
        if moves and ln > best_len:
            best_len = ln
            best_first = moves[0]
        if sleep_s > 0:
            time.sleep(sleep_s)

    if best_len < 1 or best_first is None:
        return None, api, lengths
    return best_first, api, lengths


# run one level
def _run_one_level(
    start: Board,
    llm_cfg: LLMConfig,
    rules_path: Path,
    examples_path: Path | None,
    max_steps: int,
    sleep_s: float,
    self_consistency_k: int,
    retry_on_illegal: bool,
) -> Dict[str, Any]:
    """Run Protocol B on one puzzle until win, parse failure, illegal move, or step cap."""
    b = start.copy()
    api_calls = 0
    applied = 0
    first_illegal_step: int | None = None
    retries_used = 0

    # each outer step: optionally k samples, then apply first move of winning sample
    for step in range(max_steps):
        if b.is_solved():
            return {
                "won": True,
                "api_calls": api_calls,
                "applied_moves": applied,
                "first_illegal_step": first_illegal_step,
                "retries_used": retries_used,
                "self_consistency_k": self_consistency_k,
                "retry_on_illegal": retry_on_illegal,
            }

        user = build_one_move_prompt(b, rules_path, examples_path)
        last_lengths: list[int] = []
        step_retry_done = False

        # inner loop: one retry with suffix if empty/illegal and flag set
        while True:
            if self_consistency_k <= 1:
                text = chat_text(_SYSTEM_ONE_MOVE, user, llm_cfg)
                api_calls += 1
                moves = parse_plan(text)
                mv: Tuple[str, int] | None = moves[0] if moves else None
            else:
                mv, used, last_lengths = _choose_first_move_self_consistency(
                    b, llm_cfg, user, self_consistency_k, sleep_s
                )
                api_calls += used

            if mv is None:
                if retry_on_illegal and not step_retry_done:
                    user = build_one_move_prompt(b, rules_path, examples_path) + _RETRY_USER_SUFFIX
                    step_retry_done = True
                    retries_used += 1
                    continue
                return {
                    "won": False,
                    "api_calls": api_calls,
                    "applied_moves": applied,
                    "first_illegal_step": first_illegal_step if first_illegal_step is not None else step,
                    "stop_reason": "empty_parse",
                    "retries_used": retries_used,
                    "self_consistency_k": self_consistency_k,
                    "retry_on_illegal": retry_on_illegal,
                    "last_sc_prefix_lengths": last_lengths if self_consistency_k > 1 else [],
                }

            pr = run_plan(b, [mv])  # single macro-move legality on current board
            if pr.first_illegal_index is not None:
                if retry_on_illegal and not step_retry_done:
                    user = build_one_move_prompt(b, rules_path, examples_path) + _RETRY_USER_SUFFIX
                    step_retry_done = True
                    retries_used += 1
                    continue
                if first_illegal_step is None:
                    first_illegal_step = step
                return {
                    "won": False,
                    "api_calls": api_calls,
                    "applied_moves": applied,
                    "first_illegal_step": first_illegal_step,
                    "stop_reason": "illegal_move",
                    "retries_used": retries_used,
                    "self_consistency_k": self_consistency_k,
                    "retry_on_illegal": retry_on_illegal,
                    "last_sc_prefix_lengths": last_lengths if self_consistency_k > 1 else [],
                }

            b = pr.final_board
            applied += 1
            if sleep_s > 0:
                time.sleep(sleep_s)
            break

    return {
        "won": b.is_solved(),
        "api_calls": api_calls,
        "applied_moves": applied,
        "first_illegal_step": first_illegal_step,
        "stop_reason": "max_steps",
        "retries_used": retries_used,
        "self_consistency_k": self_consistency_k,
        "retry_on_illegal": retry_on_illegal,
    }


# main
def main() -> None:
    """CLI entry: Protocol B over many levels; writes JSON with ``per_level`` API stats."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", type=Path, default=ROOT / "data" / "levels_eval.json")
    ap.add_argument("--planner", choices=("openai",), required=True)
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument("--max-levels", type=int, default=10_000)
    ap.add_argument(
        "--max-steps",
        type=int,
        default=500,
        help="Max API rounds per level (raise for harder puzzles; costs more).",
    )
    ap.add_argument("--sleep-seconds", type=float, default=0.0)
    ap.add_argument(
        "--few-shot",
        type=int,
        choices=(0, 1, 2),
        default=0,
        help="0=no few-shot; 1 or 2=toy examples in prompts/examples_fewshot_{1,2}.txt",
    )
    ap.add_argument("--out", type=Path, default=ROOT / "evaluation_outputs" / "iterative_last.json")
    ap.add_argument(
        "--self-consistency-k",
        type=int,
        default=1,
        metavar="K",
        help="Per step: K independent samples of the same prompt; pick sample with longest "
        "legal-prefix plan, apply only its first move. K=1 is baseline (one sample). ~K× API per step.",
    )
    ap.add_argument(
        "--retry-on-illegal",
        action="store_true",
        help="After empty parse or illegal first move on same board, one extra API call with a "
        "fixed retry suffix (not search; at most one retry per step). Up to ~2× API on worst steps.",
    )
    args = ap.parse_args()
    if args.self_consistency_k < 1:
        ap.error("--self-consistency-k must be >= 1")

    rows_in, meta = _load_levels_file(args.levels)
    rows_in = rows_in[: args.max_levels]

    rules_path = ROOT / "prompts" / "rules_one_move.txt"
    examples_path = _few_shot_path(args.few_shot)
    llm_cfg = load_llm_config(args.config)
    llm_cfg = LLMConfig("openai", llm_cfg.model)

    results: list[dict[str, Any]] = []
    nlv = len(rows_in)
    for li, row in enumerate(rows_in):
        board = Board.from_fogleman_string(row["board"])
        rid = row.get("id", row["board"][:8])
        opt = row.get("optimal_moves")
        print(f"[{li + 1}/{nlv}] {rid} (opt={opt}) — iterative run (may take many API calls)...", flush=True)
        r = _run_one_level(
            board,
            llm_cfg,
            rules_path,
            examples_path,
            args.max_steps,
            args.sleep_seconds,
            args.self_consistency_k,
            args.retry_on_illegal,
        )
        r["id"] = rid
        r["planner"] = args.planner
        r["optimal_moves"] = opt
        r["few_shot"] = args.few_shot
        results.append(r)
        print(
            f"    → won={r.get('won')} api_calls={r.get('api_calls')} applied_moves={r.get('applied_moves')}",
            flush=True,
        )

    wins = sum(1 for r in results if r.get("won"))
    total_api = sum(int(r.get("api_calls") or 0) for r in results)
    summary: dict[str, Any] = {
        "protocol": "iterative_one_move",
        "levels": len(results),
        "wins": wins,
        "win_rate": wins / len(results) if results else 0.0,
        "total_api_calls": total_api,
        "mean_api_calls_per_level": total_api / len(results) if results else 0.0,
        "planner": args.planner,
        "few_shot": args.few_shot,
        "max_steps": args.max_steps,
        "self_consistency_k": args.self_consistency_k,
        "retry_on_illegal": args.retry_on_illegal,
        "per_level": results,
    }
    if meta is not None:
        summary["levels_file_meta"] = meta

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_level"}, indent=2))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
