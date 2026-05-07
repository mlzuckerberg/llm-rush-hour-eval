"""LLM output line parsing (fences, list prefixes, move regex)."""

from llm.parse_output import parse_plan


# test parse plan basic
def test_parse_plan_basic():
    text = "B +2\nC -1\n"
    assert parse_plan(text) == [("B", 2), ("C", -1)]


# test parse plan skips comments and blank
def test_parse_plan_skips_comments_and_blank():
    text = "\n# hi\nM +3\n\n"
    assert parse_plan(text) == [("M", 3)]


# test parse plan strips fence
def test_parse_plan_strips_fence():
    text = "```\nA +1\nB -2\n```"
    assert parse_plan(text) == [("A", 1), ("B", -2)]


# test parse plan numbered lines
def test_parse_plan_numbered_lines():
    text = "1. B +2\n2. C -1\n"
    assert parse_plan(text) == [("B", 2), ("C", -1)]


# test parse plan allows trailing comment
def test_parse_plan_allows_trailing_comment():
    text = "M +3  # slide truck\n"
    assert parse_plan(text) == [("M", 3)]
