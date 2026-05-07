"""
Rush Hour board compatible with Michael Fogleman's reference implementation.
See: https://github.com/fogleman/rush/blob/master/model.go
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Sequence, Tuple


@dataclass
class Piece:
    """One vehicle: anchor cell, length, orientation."""

    position: int  # linear index of first cell (top-left in scan order)
    size: int
    horizontal: bool  # True = horizontal (stride 1), False = vertical (stride width)

    # stride
    def stride(self, width: int) -> int:
        return 1 if self.horizontal else width

    # row
    def row(self, width: int) -> int:
        return self.position // width

    # col
    def col(self, width: int) -> int:
        return self.position % width


@dataclass
class Board:
    """6×6 (or square) Rush Hour grid: pieces, optional walls, occupancy cache.

    Piece index 0 is the goal car ``A`` (must be horizontal per Fogleman rules).
    ``labels`` order matches ``pieces`` and is sorted alphabetically by letter.
    """

    width: int
    height: int
    pieces: List[Piece]
    walls: List[int]
    labels: List[str]  # labels[i] is board letter for piece index i (sorted alphabetically)
    occupied: List[bool] = field(default_factory=list, repr=False)

    @staticmethod
    # from fogleman string
    def from_fogleman_string(desc: str) -> "Board":
        s = int(len(desc) ** 0.5)
        if s * s != len(desc):
            raise ValueError("board string must be square")
        rows = [desc[i * s : (i + 1) * s] for i in range(s)]
        return Board.from_rows(rows)

    @staticmethod
    # from rows
    def from_rows(rows: Sequence[str]) -> "Board":
        h = len(rows)
        if h < 3:
            raise ValueError("board height must be >= 3")
        w = len(rows[0])
        if w < 3:
            raise ValueError("board width must be >= 3")
        for row in rows:
            if len(row) != w:
                raise ValueError("all rows must have same width")

        occupied = [False] * (w * h)
        positions: dict[str, list[int]] = {}
        walls: list[int] = []

        # scan grid: collect contiguous cells per letter, walls, empties
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                label = ch
                if label in (".", "o"):
                    continue
                i = y * w + x
                occupied[i] = True
                if label == "x":
                    walls.append(i)
                else:
                    positions.setdefault(label, []).append(i)

        # infer each letter as one straight piece (car/truck), anchor at min index
        labels_sorted = sorted(positions.keys())
        pieces: list[Piece] = []
        for label in labels_sorted:
            ps = sorted(positions[label])
            if len(ps) < 2:
                raise ValueError(f"piece {label} length must be >= 2")
            stride = ps[1] - ps[0]
            if stride not in (1, w):
                raise ValueError(f"piece {label} has invalid shape")
            for j in range(2, len(ps)):
                if ps[j] - ps[j - 1] != stride:
                    raise ValueError(f"piece {label} has invalid shape")
            horizontal = stride == 1
            pieces.append(Piece(ps[0], len(ps), horizontal))

        board = Board(w, h, pieces, walls, labels_sorted, [])
        board._rebuild_occupied()
        board._validate()
        return board

    # rebuild occupied
    def _rebuild_occupied(self) -> None:
        w, h = self.width, self.height
        occ = [False] * (w * h)
        for i in self.walls:
            occ[i] = True
        for p in self.pieces:
            idx = p.position
            st = p.stride(w)
            for _ in range(p.size):
                occ[idx] = True
                idx += st
        self.occupied = occ

    # validate
    def _validate(self) -> None:
        w, h = self.width, self.height
        pieces = self.pieces
        if len(pieces) < 1:
            raise ValueError("board must have at least one piece")
        if len(pieces) > 18:
            raise ValueError("board must have <= 18 pieces")
        if not pieces[0].horizontal:
            raise ValueError("primary piece must be horizontal")

        occ = [False] * (w * h)
        for i in self.walls:
            if i < 0 or i >= w * h:
                raise ValueError("wall outside grid")
            if occ[i]:
                raise ValueError("wall intersects")
            occ[i] = True

        primary_row = pieces[0].row(w)
        for i, piece in enumerate(pieces):
            if piece.size < 2:
                raise ValueError(f"piece {i} size must be >= 2")
            if i > 0 and piece.horizontal and piece.row(w) == primary_row:
                raise ValueError("no horizontal pieces on primary row")
            if piece.horizontal:
                if piece.row(w) < 0 or piece.row(w) >= h or piece.col(w) < 0 or piece.col(w) + piece.size > w:
                    raise ValueError(f"piece {i} outside grid")
            else:
                if piece.col(w) < 0 or piece.col(w) >= w or piece.row(w) < 0 or piece.row(w) + piece.size > h:
                    raise ValueError(f"piece {i} outside grid")
            idx = piece.position
            st = piece.stride(w)
            for _ in range(piece.size):
                if occ[idx]:
                    raise ValueError(f"piece {i} intersects another piece or wall")
                occ[idx] = True
                idx += st

    # copy
    def copy(self) -> "Board":
        b = Board(
            self.width,
            self.height,
            [Piece(p.position, p.size, p.horizontal) for p in self.pieces],
            list(self.walls),
            list(self.labels),
            list(self.occupied),
        )
        return b

    # target
    def target(self) -> int:
        """Left-cell index when primary car is aligned to exit (right edge)."""
        w = self.width
        p0 = self.pieces[0]
        row = p0.row(w)
        return (row + 1) * w - p0.size

    # is solved
    def is_solved(self) -> bool:
        return self.pieces[0].position == self.target()

    # board string
    def board_string(self) -> str:
        """Row-major string using original letters and o / x."""
        w, h = self.width, self.height
        grid = ["o"] * (w * h)
        for i in self.walls:
            grid[i] = "x"
        for i, piece in enumerate(self.pieces):
            ch = self.labels[i]
            idx = piece.position
            st = piece.stride(w)
            for _ in range(piece.size):
                grid[idx] = ch
                idx += st
        return "".join(grid)

    # ascii grid
    def ascii_grid(self) -> str:
        w = self.width
        s = self.board_string()
        return "\n".join(s[i * w : (i + 1) * w] for i in range(self.height))

    # list moves
    def list_moves(self) -> List[Tuple[int, int]]:
        """All legal macro-moves: ``(piece_index, signed_steps)`` (one slide to block)."""
        moves: list[tuple[int, int]] = []
        w, h = self.width, self.height
        for i, piece in enumerate(self.pieces):
            # slide until blocked: enumerate negative steps then positive along axis
            if piece.horizontal:
                x = piece.position % w
                reverse_steps = -x
                forward_steps = w - piece.size - x
                stride = 1
            else:
                y = piece.position // w
                reverse_steps = -y
                forward_steps = h - piece.size - y
                stride = w

            idx = piece.position - stride
            for steps in range(-1, reverse_steps - 1, -1):
                if self.occupied[idx]:
                    break
                moves.append((i, steps))
                idx -= stride

            idx = piece.position + piece.size * stride
            for steps in range(1, forward_steps + 1):
                if self.occupied[idx]:
                    break
                moves.append((i, steps))
                idx += stride
        return moves

    # apply move
    def apply_move(self, piece_index: int, steps: int) -> None:
        if steps == 0:
            raise ValueError("steps must be non-zero")
        piece = self.pieces[piece_index]
        w = self.width
        stride = piece.stride(w)
        idx = piece.position
        for _ in range(piece.size):
            self.occupied[idx] = False  # clear old footprint
            idx += stride
        piece.position += stride * steps
        idx = piece.position
        for _ in range(piece.size):
            self.occupied[idx] = True  # stamp new footprint (caller checked legality)
            idx += stride

    # undo move
    def undo_move(self, piece_index: int, steps: int) -> None:
        self.apply_move(piece_index, -steps)

    # label to index
    def label_to_index(self, letter: str) -> int:
        if len(letter) != 1:
            raise ValueError("expected single-character label")
        try:
            return self.labels.index(letter)
        except ValueError as e:
            raise KeyError(f"unknown piece label {letter!r}") from e


# parse fogleman line
def parse_fogleman_line(line: str) -> tuple[int, str, int | None]:
    """
    Parse a rush database line: ``OPT_MOVES BOARD36 [CLUSTER]``.
    Returns (optimal_moves, board_string, cluster_or_none).
    """
    parts = line.strip().split()  # whitespace-separated; cluster optional
    if len(parts) < 2:
        raise ValueError(f"bad line: {line!r}")
    optimal = int(parts[0])
    board = parts[1]
    cluster = int(parts[2]) if len(parts) > 2 else None
    return optimal, board, cluster
