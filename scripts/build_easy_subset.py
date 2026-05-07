#!/usr/bin/env python3
"""
Build a smaller eval JSON with only \"easier\" levels (lower optimal_moves).

Example:
  PYTHONPATH=. python scripts/build_easy_subset.py \\
    --input data/levels_eval.json --max-optimal 40 --output data/levels_easy_40.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# main
def main() -> None:
    """Filter an existing level JSON by ``optimal_moves`` cap; merge meta for provenance."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=ROOT / "data" / "levels_eval.json")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--max-optimal", type=int, default=40)
    args = ap.parse_args()

    raw = json.loads(args.input.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "levels" in raw:
        meta_in = raw.get("meta", {})
        levels = raw["levels"]
    elif isinstance(raw, list):
        meta_in = {}
        levels = raw
    else:
        raise SystemExit("bad input json")

    # filter in place from an existing eval file (keeps schema)
    kept = [r for r in levels if int(r.get("optimal_moves", 999)) <= args.max_optimal]
    meta = {
        **meta_in,
        "easy_subset": True,
        "max_optimal": args.max_optimal,
        "source_input": str(args.input),
        "original_count": len(levels),
        "kept_count": len(kept),
    }
    out = {"meta": meta, "levels": kept}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
