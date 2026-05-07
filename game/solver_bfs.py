"""
BFS optimal move count aligned with fogleman/rush solver search:
each transition is one slide (any distance); the solver disallows
moving the same piece twice in a row (see solver.go search loop).
"""

from __future__ import annotations

from collections import deque
from typing import Deque, List, Optional, Tuple

from game.board import Board

# (piece positions tuple, last_moved_piece_index or -1)
State = Tuple[Tuple[int, ...], int]


# state from board
def _state_from_board(b: Board) -> Tuple[int, ...]:
    return tuple(p.position for p in b.pieces)


# board from positions
def _board_from_positions(template: Board, positions: Tuple[int, ...]) -> Board:
    nb = template.copy()
    for i, pos in enumerate(positions):
        nb.pieces[i].position = pos
    nb._rebuild_occupied()
    return nb


# bfs optimal moves
def bfs_optimal_moves(
    start: Board,
    forbid_consecutive_same_piece: bool = True,
    max_states: int = 2_000_000,
) -> Optional[int]:
    """
    Minimum number of moves to solve. Returns None if unsolved within max_states
    or unreachable in search space.
    """
    if start.is_solved():
        return 0

    start_positions = _state_from_board(start)
    start_state: State = (start_positions, -1)
    visited: set[State] = {start_state}
    q: Deque[tuple[State, int]] = deque([(start_state, 0)])

    # state = (tuple of piece positions, last piece moved); edges match fogleman search
    while q:
        (positions, last), depth = q.popleft()
        if len(visited) > max_states:
            return None

        board = _board_from_positions(start, positions)
        for piece_idx, steps in board.list_moves():
            if forbid_consecutive_same_piece and piece_idx == last:
                continue  # matches rush solver.go — no immediate undo-style bounce
            nb = board.copy()
            nb.apply_move(piece_idx, steps)
            new_positions = _state_from_board(nb)
            new_last = piece_idx
            nxt: State = (new_positions, new_last)
            if nxt in visited:
                continue
            if nb.is_solved():
                return depth + 1
            visited.add(nxt)
            q.append((nxt, depth + 1))
    return None


# bfs solution moves
def bfs_solution_moves(
    start: Board,
    forbid_consecutive_same_piece: bool = True,
    max_states: int = 2_000_000,
) -> Optional[List[Tuple[int, int]]]:
    """Reconstruct one optimal path as ``(piece_index, signed_steps)``, or ``None``.

    Branching matches the reference ``forbid_consecutive_same_piece`` convention
    used for ``optimal_moves`` labels in the Fogleman database.
    """
    if start.is_solved():
        return []

    start_state: State = (_state_from_board(start), -1)
    parent_move: dict[State, tuple[State, tuple[int, int]] | None] = {start_state: None}
    q: Deque[State] = deque([start_state])
    goal_state: State | None = None

    while q:
        st = q.popleft()
        if len(parent_move) > max_states:
            return None
        positions, last = st
        board = _board_from_positions(start, positions)
        for piece_idx, steps in board.list_moves():
            if forbid_consecutive_same_piece and piece_idx == last:
                continue
            nb = board.copy()
            nb.apply_move(piece_idx, steps)
            nxt: State = (_state_from_board(nb), piece_idx)
            if nxt in parent_move:
                continue
            parent_move[nxt] = (st, (piece_idx, steps))
            if nb.is_solved():
                goal_state = nxt
                q.clear()
                break
            q.append(nxt)

    if goal_state is None:
        return None

    path: list[tuple[int, int]] = []
    cur = goal_state
    while cur != start_state:
        pm = parent_move.get(cur)
        if pm is None:
            return None
        prev, move = pm
        path.append(move)
        cur = prev
    path.reverse()  # was goal → start
    return path
