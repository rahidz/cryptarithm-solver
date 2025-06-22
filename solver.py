from or_tools_solver import solve_with_cp_sat

def solve_cryptarithm(puzzle_string, base=10, constraints=None):
    """
    Solves a cryptarithm puzzle.
    This function now acts as a simple wrapper around the CP-SAT solver.
    """
    return solve_with_cp_sat(
        puzzle_string,
        base=base,
        constraints=constraints
    )