#!/usr/bin/env python3
"""
Compare Protocol A (``run_eval`` JSON) vs Protocol B (``run_iterative_eval`` JSON).

Joins on **level id intersection** so iterative runs on a prefix can be compared
fairly to full-set single-shot logs. Writes Markdown (stdout / ``--out``).

Usage:
  PYTHONPATH=. python scripts/compare_protocols.py \\
    --protocol-a evaluation_outputs/openai_levels_eval.json \\
    --protocol-b evaluation_outputs/openai_iterative_20.json \\
    --out evaluation_outputs/protocol_comparison.md
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


# load json
def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# load per level
def _load_per_level(path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    data = _load_json(path)
    protocol = str(data.get("protocol", "single_shot_full_plan"))
    return protocol, data.get("per_level", [])


# main
def main() -> None:
    """Emit matched-id Markdown table for paper / TA review."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--protocol-a", type=Path, required=True, help="run_eval openai JSON")
    ap.add_argument("--protocol-b", type=Path, required=True, help="run_iterative_eval JSON")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    data_a = _load_json(args.protocol_a)
    data_b = _load_json(args.protocol_b)
    rows_a = data_a.get("per_level", [])
    rows_b = data_b.get("per_level", [])

    by_a = {r["id"]: r for r in rows_a if "id" in r}
    by_b = {r["id"]: r for r in rows_b if "id" in r}
    ids = sorted(set(by_a) & set(by_b))  # fair compare if b only ran a prefix

    lines: list[str] = []
    lines.append("# Protocol A vs B (matched level ids)\n")
    lines.append(f"- **Protocol A file:** `{args.protocol_a}`\n")
    lines.append(f"- **Protocol B file:** `{args.protocol_b}`\n")
    lines.append(f"- **Levels compared:** {len(ids)} (intersection of ids)\n")
    if data_b.get("protocol") == "iterative_one_move":
        sk = data_b.get("self_consistency_k")
        rz = data_b.get("retry_on_illegal")
        if sk is not None or rz is not None:
            lines.append(
                f"- **Protocol B options (from JSON header):** "
                f"`self_consistency_k={sk!r}`, `retry_on_illegal={rz!r}`\n"
            )

    if not ids:
        lines.append("\n*No overlapping level ids — check file paths.*\n")
        text = "".join(lines)
        print(text)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        return

    wins_a = sum(1 for i in ids if by_a[i].get("won"))
    wins_b = sum(1 for i in ids if by_b[i].get("won"))
    first_ok_a = sum(1 for i in ids if int(by_a[i].get("applied") or 0) >= 1)
    applied_b = [int(by_b[i].get("applied_moves") or 0) for i in ids]
    api_b = [int(by_b[i].get("api_calls") or 0) for i in ids]

    lines.append("\n## Headline metrics\n")
    lines.append("| Metric | Protocol A (single-shot) | Protocol B (iterative) |\n")
    lines.append("|--------|---------------------------|-------------------------|\n")
    lines.append(f"| Win rate | {wins_a / len(ids):.3f} | {wins_b / len(ids):.3f} |\n")
    lines.append(
        f"| First move legal rate | {first_ok_a / len(ids):.3f} | — |\n"
    )
    lines.append(
        f"| Mean legal prefix length (before stop) | {sum(int(by_a[i].get('applied') or 0) for i in ids) / len(ids):.2f} | "
        f"{sum(applied_b) / len(ids):.2f} |\n"
    )
    lines.append(f"| Mean API calls per level | 1.0 | {sum(api_b) / len(ids):.2f} |\n")

    # histogram of how many moves protocol b got down before stop
    hist = Counter(applied_b)
    lines.append("\n## Protocol B — distribution of `applied_moves` (legal moves before failure or cap)\n")
    lines.append("| applied_moves | Count |\n")
    lines.append("|---------------|-------|\n")
    for k in sorted(hist.keys()):
        lines.append(f"| {k} | {hist[k]} |\n")

    # bucket ids using optimal_moves carried on protocol a rows
    bin_ids: dict[str, list[str]] = defaultdict(list)
    for lid in ids:
        o = by_a[lid].get("optimal_moves")
        if o is None:
            continue
        if o <= 42:
            bin_ids["38-42"].append(lid)
        elif o <= 47:
            bin_ids["43-47"].append(lid)
        elif o <= 52:
            bin_ids["48-52"].append(lid)
        else:
            bin_ids["53-60"].append(lid)

    lines.append("\n## By optimal-move bin (same ids as above)\n")
    lines.append("| Bin | n | A win | B win | B mean applied |\n")
    lines.append("|-----|---|-------|-------|----------------|\n")
    for bname in sorted(bin_ids.keys()):
        g = bin_ids[bname]
        if not g:
            continue
        wa = sum(1 for lid in g if by_a[lid].get("won")) / len(g)
        wb = sum(1 for lid in g if by_b[lid].get("won")) / len(g)
        mb = sum(int(by_b[lid].get("applied_moves") or 0) for lid in g) / len(g)
        lines.append(f"| {bname} | {len(g)} | {wa:.3f} | {wb:.3f} | {mb:.2f} |\n")

    text = "".join(lines)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
