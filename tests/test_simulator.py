"""``run_plan`` legality and oracle trajectory on sample boards."""

from game.board import Board
from game.simulator import moves_from_indices, run_plan
from game.solver_bfs import bfs_solution_moves


# test oracle plan always wins first puzzle
def test_oracle_plan_always_wins_first_puzzle():
    s = "IBBxooIooLDDJAALooJoKEEMFFKooMGGHHHM"
    b = Board.from_fogleman_string(s)
    sol = bfs_solution_moves(b, True)
    assert sol is not None
    letters = moves_from_indices(b, sol)
    pr = run_plan(b, letters)
    assert pr.won
    assert pr.first_illegal_index is None


# test illegal move stops
def test_illegal_move_stops():
    s = "IBBxooIooLDDJAALooJoKEEMFFKooMGGHHHM"
    b = Board.from_fogleman_string(s)
    pr = run_plan(b, [("A", 99)])  # impossible slide
    assert not pr.won
    assert pr.first_illegal_index == 0
