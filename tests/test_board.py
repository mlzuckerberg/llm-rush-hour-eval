"""Board parsing, BFS optima vs database labels, and invariants."""

import json
from pathlib import Path

from game.board import Board, parse_fogleman_line
from game.solver_bfs import bfs_optimal_moves, bfs_solution_moves


# test parse fogleman line
def test_parse_fogleman_line():
    opt, board, cluster = parse_fogleman_line(
        "60 IBBxooIooLDDJAALooJoKEEMFFKooMGGHHHM 2332"
    )
    assert opt == 60
    assert len(board) == 36
    assert cluster == 2332


# test first puzzle bfs matches database
def test_first_puzzle_bfs_matches_database():
    _, s, _ = parse_fogleman_line("60 IBBxooIooLDDJAALooJoKEEMFFKooMGGHHHM 2332")
    b = Board.from_fogleman_string(s)
    assert bfs_optimal_moves(b, True) == 60  # must match opt in first column of db line
    sol = bfs_solution_moves(b, True)
    assert len(sol) == 60
    b2 = b.copy()
    for mv in sol:
        b2.apply_move(*mv)
    assert b2.is_solved()


# test sample levels json match bfs
def test_sample_levels_json_match_bfs():
    path = Path(__file__).resolve().parents[1] / "data" / "sample_levels.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        b = Board.from_fogleman_string(row["board"])
        got = bfs_optimal_moves(b, True)
        assert got == row["optimal_moves"], (row["id"], got, row["optimal_moves"])
