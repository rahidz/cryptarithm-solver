"""Structured and backwards-compatible cryptarithm interfaces."""

from or_tools_solver import (
    solve_puzzle,
    solve_with_cp_sat,
    inspect_puzzle,
    validate_assignment,
    validate_assignment_strict,
)

__all__ = [
    "solve_puzzle",
    "inspect_puzzle",
    "validate_assignment",
    "validate_assignment_strict",
    "solve_cryptarithm",
]


def solve_cryptarithm(puzzles, base=10, constraints=None):
    return solve_with_cp_sat(puzzles, base, constraints)
