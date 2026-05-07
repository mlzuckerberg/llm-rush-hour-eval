#!/usr/bin/env python3
"""
Build a fixed eval JSON stratified by optimal_moves bins (for horizon / difficulty tables).

Example:
  PYTHONPATH=. python scripts/build_stratified_eval.py \\
    --input data/rush1000.txt \\
    --output data/levels_eval.json \\
    --bins 38-42,43-47,48-52,53-60 \\
    --per-bin 18 --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.board import Board, parse_fogleman_line  # noqa: E402


# parse bins
def _parse_bins(spec: str) -> List[Tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        lo_s, hi_s = part.split("-", 1)
        lo, hi = int(lo_s), int(hi_s)
        if lo > hi:
            lo, hi = hi, lo
        out.append((lo, hi))
    if not out:
        raise ValueError("no bins")
    return out


# main
def main() -> None:
    """Build stratified ``levels_eval``-style JSON from a Fogleman text database."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument(
        "--bins",
        type=str,
        default="38-42,43-47,48-52,53-60",
        help="Comma-separated inclusive ranges like 38-42,43-47",
    )
    ap.add_argument("--per-bin", type=int, default=18)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    bins = _parse_bins(args.bins)
    rng = random.Random(args.seed)

    lines = [ln.strip() for ln in args.input.read_text(encoding="utf-8").splitlines() if ln.strip()]
    pool: list[dict] = []
    # parse every valid line into a candidate row (skip malformed)
    for i, ln in enumerate(lines):
        try:
            opt, board, cluster = parse_fogleman_line(ln)
            Board.from_fogleman_string(board)
        except Exception:
            continue
        pool.append(
            {
                "id": f"{args.input.stem}-{i}",
                "optimal_moves": opt,
                "board": board,
                "cluster": cluster,
            }
        )

    # take up to per_bin from each range (after shuffle)
    chosen: list[dict] = []
    manifest_bins: dict[str, dict] = {}
    for lo, hi in bins:
        key = f"{lo}-{hi}"
        candidates = [r for r in pool if lo <= r["optimal_moves"] <= hi]
        rng.shuffle(candidates)
        take = candidates[: args.per_bin]
        manifest_bins[key] = {"available": len(candidates), "selected": len(take)}
        chosen.extend(take)

    # de-dup by board string while preserving order
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in chosen:
        if r["board"] in seen:
            continue
        seen.add(r["board"])
        deduped.append(r)

    meta = {
        "source_file": str(args.input),
        "bins": args.bins,
        "per_bin_target": args.per_bin,
        "seed": args.seed,
        "counts_per_bin": manifest_bins,
        "total_selected": len(deduped),
    }
    out_obj = {"meta": meta, "levels": deduped}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out_obj, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    print(f"Wrote {len(deduped)} unique levels to {args.output}")


if __name__ == "__main__":
    main()
