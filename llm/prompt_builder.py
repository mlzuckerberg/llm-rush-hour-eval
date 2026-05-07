"""Build user prompts for Protocol A (full plan) and Protocol B (one move)."""

from __future__ import annotations

from pathlib import Path

from game.board import Board


# read optional comments filtered
def _read_optional_comments_filtered(path: Path) -> str:
    # few-shot files allow # comments so we can annotate examples without sending them
    if not path.exists():
        return ""
    lines = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(ln.rstrip())
    return "\n".join(lines).strip()


# build full plan prompt
def build_full_plan_prompt(
    board: Board,
    rules_path: Path,
    examples_path: Path | None = None,
) -> str:
    """Protocol A user message: rules + ASCII board + optional few-shot block."""
    rules = rules_path.read_text(encoding="utf-8").strip()
    parts = [rules, "", "Current puzzle (6 rows, 6 columns per row):", board.ascii_grid(), ""]
    if examples_path and examples_path.exists():
        ex = _read_optional_comments_filtered(examples_path)
        if ex:
            parts.extend(["Few-shot examples:", ex, ""])
    parts.append("Output the full move list now (move lines only).")
    return "\n".join(parts)


# build one move prompt
def build_one_move_prompt(
    board: Board,
    rules_path: Path,
    examples_path: Path | None = None,
) -> str:
    """Protocol B user message: one-move rules + current board (+ few-shot)."""
    rules = rules_path.read_text(encoding="utf-8").strip()
    parts = [rules, "", "Current board:", board.ascii_grid(), ""]
    if examples_path and examples_path.exists():
        ex = _read_optional_comments_filtered(examples_path)
        if ex:
            parts.extend(["Few-shot examples:", ex, ""])
    parts.append("Output your single move line now.")
    return "\n".join(parts)
