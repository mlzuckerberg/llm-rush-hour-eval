#!/usr/bin/env python3
"""
Compute simple CI + p-value stats from saved evaluation JSON files.

This script intentionally uses familiar reporting:
- 95% CI for proportions (normal approximation)
- 95% CI for mean differences
- paired t-test p-values for matched A vs B comparisons
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

import mpmath as mp

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation_outputs"


# load rows
def load_rows(name: str) -> list[dict]:
    return json.loads((OUT / name).read_text(encoding="utf-8"))["per_level"]


# proportion ci
def proportion_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    p = k / n
    se = math.sqrt(p * (1 - p) / n)
    return p, max(0.0, p - z * se), min(1.0, p + z * se)


# mean ci
def mean_ci(xs: list[float], z: float = 1.96) -> tuple[float, float, float]:
    n = len(xs)
    m = sum(xs) / n
    if n < 2:
        return m, m, m
    sd = statistics.stdev(xs)
    se = sd / math.sqrt(n)
    return m, m - z * se, m + z * se


# t two sided p
def t_two_sided_p(t: float, df: int) -> float:
    x = df / (df + t * t)
    i = mp.betainc(df / 2, 0.5, 0, x, regularized=True)
    cdf = 1 - 0.5 * i if t >= 0 else 0.5 * i
    return float(2 * min(cdf, 1 - cdf))


# paired t
def paired_t(diff: list[float]) -> tuple[float, float]:
    if len(diff) < 2:
        return 0.0, 1.0
    sd = statistics.stdev(diff)
    if sd == 0:
        return 0.0, 1.0
    m = sum(diff) / len(diff)
    t = m / (sd / math.sqrt(len(diff)))
    return t, t_two_sided_p(t, len(diff) - 1)


# main
def main() -> None:
    for name in ("openai_levels_eval.json", "gpt4o_levels_eval.json"):
        rows = load_rows(name)
        n = len(rows)
        wins = sum(1 for r in rows if r.get("won"))
        first = sum(1 for r in rows if r.get("applied", 0) >= 1)
        wp, wl, wu = proportion_ci(wins, n)
        fp, fl, fu = proportion_ci(first, n)
        print(f"{name}: win={wp:.3f} [{wl:.3f},{wu:.3f}] first={fp:.3f} [{fl:.3f},{fu:.3f}]")

    for a_name, b_name, tag in (
        ("openai_levels_eval.json", "openai_iterative_20.json", "mini"),
        ("gpt4o_levels_eval.json", "gpt4o_iterative_20.json", "gpt4o"),
    ):
        a_rows = {r["id"]: r for r in load_rows(a_name)}
        b_rows = {r["id"]: r for r in load_rows(b_name)}
        ids = sorted(set(a_rows) & set(b_rows))
        d_applied = [b_rows[i].get("applied_moves", 0) - a_rows[i].get("applied", 0) for i in ids]
        dm, dl, du = mean_ci(d_applied)
        t, p = paired_t(d_applied)
        print(f"A_vs_B {tag}: diff={dm:.3f} [{dl:.3f},{du:.3f}] t={t:.3f} p={p:.3f}")

    for base_name, sc_name, tag in (
        ("openai_iterative_20.json", "openai_iterative_20_sc3_retry.json", "mini"),
        ("gpt4o_iterative_20.json", "gpt4o_iterative_20_sc3_retry.json", "gpt4o"),
    ):
        base_rows = {r["id"]: r for r in load_rows(base_name)}
        sc_rows = {r["id"]: r for r in load_rows(sc_name)}
        ids = sorted(set(base_rows) & set(sc_rows))
        for metric in ("applied_moves", "api_calls"):
            diff = [sc_rows[i].get(metric, 0) - base_rows[i].get(metric, 0) for i in ids]
            dm, dl, du = mean_ci(diff)
            t, p = paired_t(diff)
            p_str = "<0.001" if p < 0.001 else f"{p:.3f}"
            print(f"SC_vs_base {tag} {metric}: diff={dm:.3f} [{dl:.3f},{du:.3f}] t={t:.3f} p={p_str}")


if __name__ == "__main__":
    main()
