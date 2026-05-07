"""Random legal-move rollout baseline (no LLM)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from game.board import Board


@dataclass
class RolloutResult:
    """Result of a random legal-move trajectory."""

    won: bool
    num_moves: int


# random rollout
def random_rollout(start: Board, rng: random.Random, max_moves: int = 5000) -> RolloutResult:
    """Uniform random legal macro-moves until win, deadlock, or ``max_moves``."""
    b = start.copy()
    for t in range(max_moves):
        if b.is_solved():
            return RolloutResult(True, t)
        moves = b.list_moves()
        if not moves:
            return RolloutResult(False, t)  # stuck (shouldn't happen on standard puzzles)
        piece_idx, steps = rng.choice(moves)
        b.apply_move(piece_idx, steps)
    return RolloutResult(b.is_solved(), max_moves)  # hit step budget
