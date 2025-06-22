# Cryptarithm Solver

This project is a Python application designed to solve cryptarithmetic puzzles. A cryptarithm is a mathematical puzzle where letters are substituted for digits. The goal is to find the digit corresponding to each letter so that the given mathematical equation holds true.

For example, `SEND + MORE = MONEY` can be solved as `9567 + 1085 = 10652`.

## Features

*   **Multiple Operations**: Solves puzzles involving addition (`+`), subtraction (`-`), multiplication (`*`), division (`/`), and exponentiation (`**`).
*   **Optimized Addition Solver**: Utilizes a fast, column-wise backtracking algorithm for addition-only puzzles, significantly improving performance.
*   **Arbitrary Base Support**: Solves puzzles in different numerical bases, from base 2 to base 36.
*   **Constraints**: Allows users to provide constraints by pre-assigning digits to specific letters (e.g., `M=1`).
*   **Safe Evaluation**: Uses a secure, custom-built expression evaluator to prevent arbitrary code execution when solving generic puzzles.

## How to Run

1.  Ensure you have Python 3 installed.
2.  Run the main script from your terminal:
    ```bash
    python main.py
    ```
3.  Follow the interactive prompts to enter the puzzle, optional constraints, and the base.

### Example Session

```
Enter a cryptarithm puzzle: SEND + MORE = MONEY
Enter constraints (e.g., O=3, R=4), or press Enter for none:
Enter the base (default is 10):
Solving: SEND + MORE = MONEY in base 10 with constraints {}
Solution: 9567 + 1085 = 10652

Solved in 0.0120 seconds.
```

## Examples

This solver can handle a variety of puzzles:

*   **Classic Addition**: `SEND + MORE = MONEY` -> `9567 + 1085 = 10652`
*   **Multiplication**: `ABCD * 9 = DCBA` -> `1089 * 9 = 9801`
*   **Different Bases**: `ALFRED / E = NEUMAN` in base 9 -> `704836 / 3 = 231572`
*   **With Constraints**: `WRONG + WRONG = RIGHT` with `O=3` -> `49306 + 49306 = 98612`

## Project Structure

*   `main.py`: The main entry point for the application. It handles user input and orchestrates the solving process.
*   `parser.py`: Contains the logic for parsing the puzzle string into a structured format (words and unique letters) that the solver can process.
*   `solver.py`: Houses the core puzzle-solving logic. It intelligently delegates tasks to the appropriate solver based on the puzzle's operators.
*   `evaluator.py`: Implements a safe `eval()` alternative to securely evaluate mathematical expressions by parsing them into an Abstract Syntax Tree (AST) and only allowing a whitelist of simple arithmetic operations.
*   `test_solver.py`: Contains a comprehensive suite of unit tests to ensure the correctness of all modules and functionalities.

## How It Works

The application employs a two-pronged approach to solving puzzles, chosen based on the operators present in the input string.

### 1. Optimized Addition Solver (`_solve_addition_puzzle`)

If the puzzle only contains the `+` operator, a highly efficient, column-wise backtracking algorithm is used.

1.  The puzzle is parsed into addends and a result, which are then padded and aligned by columns.
2.  The solver works from the rightmost column to the left, assigning digits to letters.
3.  It uses backtracking to explore valid digit assignments for each column, carrying over values to the next column as needed.
4.  This avoids generating unnecessary permutations for the entire set of letters, making it much faster for addition problems.

### 2. Generic Solver (`_solve_generic_puzzle`)

For puzzles involving other operators (`*`, `/`, `-`, etc.), a more general brute-force approach is used.

1.  **Parse**: The `parser.py` module extracts all unique letters from the puzzle.
2.  **Permute**: It generates all possible permutations of available digits for the set of unique letters, while respecting any user-defined constraints.
3.  **Evaluate**: For each permutation:
    *   A mapping from letters to digits is created.
    *   Leading zero assignments are discarded (e.g., the first letter of a multi-digit number cannot be '0').
    *   The letters in the puzzle are substituted with their assigned digits to form a numerical equation.
    *   The `safe_eval()` function in `evaluator.py` evaluates the equation. The `int()` function is explicitly used on each number in the equation string to handle different bases correctly.
4.  **Return**: If an evaluated equation is true, the solution is returned. If all permutations are tested without a match, it reports that no solution was found.