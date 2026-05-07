#!/usr/bin/env python3
"""
Sample levels from a Fogleman-format text file (e.g. rush1000.txt or rush.txt).

Usage:
  PYTHONPATH=. python scripts/prepare_dataset.py --input data/rush1000.txt \\
      --output data/levels_sampled.json --n 120 --seed 42

Lines must look like: OPTIMAL_MOVES BOARD36 [CLUSTER]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from game.board import Board, parse_fogleman_line  # noqa: E402


# main
def main() -> None:
    """Random sample of valid DB lines into a small JSON for smoke tests."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    lines = [ln.strip() for ln in args.input.read_text().splitlines() if ln.strip()]
    records = []
    for i, ln in enumerate(lines):
        try:
            opt, board, cluster = parse_fogleman_line(ln)
            Board.from_fogleman_string(board)  # reject lines that don't decode as boards
        except Exception:
            continue
        records.append(
            {
                "id": f"{args.input.stem}-{i}",
                "optimal_moves": opt,
                "board": board,
                "cluster": cluster,
            }
        )

    if len(records) <= args.n:
        chosen = records
    else:
        chosen = rng.sample(records, args.n)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(chosen, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(chosen)} levels to {args.output}")


if __name__ == "__main__":
    main()
