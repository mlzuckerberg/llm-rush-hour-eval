"""Parse LLM text into Rush Hour moves (LETTER STEPS per line)."""

from __future__ import annotations

import re
from typing import List, Tuple

from game.simulator import Move

# Lines like "B +2" or "M -1"; trailing text on the same line is ignored.
_MOVE_LINE = re.compile(r"^([A-Z])\s*([+-]?\d+)(?:\s.*)?$")
_LIST_PREFIX = re.compile(r"^(?:\d+\.|[-*+])\s+")


# strip markdown fence
def _strip_markdown_fence(text: str) -> str:
    t = text.strip()
    if not t.startswith("```"):
        return t
    lines = t.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


# strip list prefix
def _strip_list_prefix(line: str) -> str:
    s = line.strip()
    while True:
        m = _LIST_PREFIX.match(s)
        if not m:
            break
        s = s[m.end() :].lstrip()
    return s


# parse plan
def parse_plan(text: str) -> List[Move]:
    """Extract ordered ``(LETTER, signed_steps)`` moves; skip non-matching lines."""
    text = _strip_markdown_fence(text)
    moves: list[Move] = []
    for raw in text.splitlines():
        line = _strip_list_prefix(raw)
        # skip blanks and pseudo-comments (model sometimes emits these)
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        m = _MOVE_LINE.match(line)
        if not m:
            continue  # narration / bullets we don't parse as moves
        letter, steps_s = m.group(1), m.group(2)
        moves.append((letter, int(steps_s)))
    return moves
