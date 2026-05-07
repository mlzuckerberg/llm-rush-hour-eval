#!/usr/bin/env python3
"""
List non-winning levels from a ``run_eval`` JSON (for ``--debug`` reruns or error mining).

Usage:
  PYTHONPATH=. python scripts/extract_failures.py evaluation_outputs/openai_eval.json
  PYTHONPATH=. python scripts/extract_failures.py evaluation_outputs/openai_eval.json --csv failures.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


# main
def main() -> None:
    """Print failure ids to stdout; optional ``--csv`` with all per-level columns."""
    ap = argparse.ArgumentParser()
    ap.add_argument("run_json", type=Path)
    ap.add_argument("--csv", type=Path, default=None)
    args = ap.parse_args()

    data = json.loads(args.run_json.read_text(encoding="utf-8"))
    rows = [r for r in data.get("per_level", []) if not r.get("won")]  # oracle wins always — mostly llm use
    print(f"Failures: {len(rows)} / {data.get('levels', '?')}\n")
    for r in rows:
        print(
            r.get("id"),
            "illegal_at=",
            r.get("illegal_at"),
            "applied=",
            r.get("applied"),
            "opt=",
            r.get("optimal_moves"),
        )

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        keys = sorted({k for r in rows for k in r.keys()})
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    main()
