#!/usr/bin/env python3
"""
Summarize one or more evaluation JSON files (Markdown + optional CSV): Protocol A
(`run_eval.py`) and/or Protocol B (`run_iterative_eval.py`).

Usage:
  PYTHONPATH=. python scripts/aggregate_runs.py evaluation_outputs/oracle_eval.json
  PYTHONPATH=. python scripts/aggregate_runs.py a.json b.json --csv out/summary.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any, Dict, List


# opt hist
def _opt_hist(per_level: List[Dict[str, Any]]) -> Dict[str, int]:
    # same bin edges as levels_eval.json stratification
    h: dict[str, int] = {}
    for r in per_level:
        o = r.get("optimal_moves")
        if o is None:
            continue
        if o <= 42:
            k = "38-42"
        elif o <= 47:
            k = "43-47"
        elif o <= 52:
            k = "48-52"
        else:
            k = "53-60"
        h[k] = h.get(k, 0) + 1
    return h


# win rate by bin
def _win_rate_by_bin(per_level: List[Dict[str, Any]]) -> Dict[str, float]:
    bins: dict[str, list[bool]] = {}
    for r in per_level:
        o = r.get("optimal_moves")
        if o is None:
            continue
        if o <= 42:
            k = "38-42"
        elif o <= 47:
            k = "43-47"
        elif o <= 52:
            k = "48-52"
        else:
            k = "53-60"
        bins.setdefault(k, []).append(bool(r.get("won")))
    out: dict[str, float] = {}
    for k, wins in bins.items():
        out[k] = sum(1 for w in wins if w) / len(wins) if wins else 0.0
    return out


# applied or moves
def _applied_or_moves(r: Dict[str, Any]) -> int:
    """Protocol A uses `applied`; Protocol B iterative uses `applied_moves`."""
    return int(r.get("applied") or r.get("applied_moves") or 0)


# summarize
def summarize(path: Path) -> Dict[str, Any]:
    """One-row dict of headline metrics for a single ``run_eval`` or iterative JSON."""
    data = json.loads(path.read_text(encoding="utf-8"))
    per = data.get("per_level", [])
    opts = [r.get("optimal_moves") for r in per if r.get("optimal_moves") is not None]
    row: dict[str, Any] = {
        "file": str(path),
        "planner": data.get("planner"),
        "protocol": data.get("protocol"),
        "levels": data.get("levels"),
        "wins": data.get("wins"),
        "win_rate": data.get("win_rate"),
        "median_optimal": float(statistics.median(opts)) if opts else None,
    }
    for k in ("self_consistency_k", "retry_on_illegal"):
        if k in data:
            row[k] = data[k]
    if per and "won" in per[0]:
        row["win_rate_by_bin"] = _win_rate_by_bin(per)
    has_a = any("plan_len_parsed" in r for r in per)  # protocol a json
    has_b_moves = any("applied_moves" in r for r in per)  # iterative json
    if per and (has_a or has_b_moves):
        n = len(per)
        first_ok = sum(1 for r in per if _applied_or_moves(r) >= 1)
        row["first_move_valid_rate"] = first_ok / n if n else 0.0
        row["mean_applied_prefix"] = (
            float(statistics.mean(_applied_or_moves(r) for r in per)) if per else 0.0
        )
        if has_a:
            row["mean_parsed_plan_len"] = float(
                statistics.mean(int(r.get("plan_len_parsed") or 0) for r in per)
            )
        if has_b_moves or any(r.get("api_calls") is not None for r in per):
            ac = [int(r["api_calls"]) for r in per if r.get("api_calls") is not None]
            if ac:
                row["mean_api_calls_per_level"] = float(statistics.mean(ac))
    return row


# main
def main() -> None:
    """Print Markdown tables across runs; optional ``--csv`` for spreadsheets."""
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", type=Path, help="run_eval JSON outputs")
    ap.add_argument("--csv", type=Path, default=None)
    args = ap.parse_args()

    rows = [summarize(p) for p in args.runs]

    has_llm_cols = any("first_move_valid_rate" in r for r in rows)
    print("## Summary\n")
    if has_llm_cols:
        print(
            "| File | Planner | Levels | Wins | Win rate | Median opt | "
            "1st move OK | Mean applied | Mean parsed len | Mean API |"
        )
        print(
            "|------|---------|--------|------|----------|------------|"
            "-------------|----------------|-----------------|----------|"
        )
    else:
        print("| File | Planner | Levels | Wins | Win rate | Median opt |")
        print("|------|---------|--------|------|----------|------------|")
    for r in rows:
        mo = r.get("median_optimal")
        mo_s = f"{mo:.1f}" if mo is not None else ""
        wr = r.get("win_rate")
        wr_s = f"{wr:.3f}" if isinstance(wr, (int, float)) else ""
        base = (
            f"| `{Path(r['file']).name}` | {r.get('planner')} | {r.get('levels')} | "
            f"{r.get('wins')} | {wr_s} | {mo_s} |"
        )
        if has_llm_cols:
            f1 = r.get("first_move_valid_rate")
            mp = r.get("mean_applied_prefix")
            ml = r.get("mean_parsed_plan_len")
            ma = r.get("mean_api_calls_per_level")
            f1_s = f"{f1:.3f}" if isinstance(f1, (int, float)) else ""
            mp_s = f"{mp:.2f}" if isinstance(mp, (int, float)) else ""
            ml_s = f"{ml:.1f}" if isinstance(ml, (int, float)) else "—"
            ma_s = f"{ma:.1f}" if isinstance(ma, (int, float)) else "—"
            base += f" {f1_s} | {mp_s} | {ml_s} | {ma_s} |"
        print(base)

    for r in rows:
        br = r.get("win_rate_by_bin")
        if not br:
            continue
        print(f"\n### Win rate by optimal-move bin — `{Path(r['file']).name}`\n")
        print("| Bin | Win rate |")
        print("|-----|----------|")
        for k in sorted(br.keys()):
            print(f"| {k} | {br[k]:.3f} |")

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        keys = sorted(
            {kk for row in rows for kk in row.keys() if kk not in ("win_rate_by_bin",)}
        )
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for row in rows:
                flat = {k: row.get(k) for k in keys}
                w.writerow(flat)
        print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    main()
