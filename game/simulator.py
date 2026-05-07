"""Apply parsed LLM move lists to a :class:`~game.board.Board` (Protocol A scoring)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Set, Tuple

from game.board import Board

Move = Tuple[str, int]  # (piece letter, signed steps)


@dataclass
class PlanResult:
    """Outcome of executing a move sequence from a fixed start state."""

    won: bool
    num_applied: int
    first_illegal_index: int | None  # 0-based index in the input list
    final_board: Board


# legal set
def _legal_set(board: Board) -> Set[Tuple[int, int]]:
    return set(board.list_moves())


# run plan
def run_plan(
    start: Board,
    moves: Sequence[Move],
    max_moves: int = 500,
) -> PlanResult:
    """Apply ``moves`` in order until illegal, win, or ``max_moves`` cap.

    ``num_applied`` counts moves successfully applied before stop; if the first
    move is illegal, ``num_applied == 0`` and ``first_illegal_index == 0``.
    """
    b = start.copy()
    for i, (letter, steps) in enumerate(moves):
        if i >= max_moves:
            return PlanResult(False, i, i, b)
        try:
            idx = b.label_to_index(letter)
        except KeyError:
            return PlanResult(False, i, i, b)  # unknown vehicle label
        legal = _legal_set(b)
        if (idx, steps) not in legal:
            return PlanResult(False, i, i, b)  # not a single legal slide from list_moves
        b.apply_move(idx, steps)
        if b.is_solved():
            return PlanResult(True, i + 1, None, b)
    # exhausted plan without win (prefix may still be all legal)
    return PlanResult(b.is_solved(), len(moves), None, b)


# moves from indices
def moves_from_indices(board: Board, idx_steps: Iterable[Tuple[int, int]]) -> List[Move]:
    """Turn BFS ``(piece_index, steps)`` tuples into letter moves for ``run_plan``."""
    return [(board.labels[i], s) for i, s in idx_steps]
