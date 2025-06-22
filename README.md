# Cryptarithm Solver

This project is a Python application designed to solve cryptarithmetic puzzles. A cryptarithm is a mathematical puzzle where letters are substituted for digits. The goal is to find the digit corresponding to each letter so that the given mathematical equation holds true.

For example, `SEND + MORE = MONEY` can be solved as `9567 + 1085 = 10652`.

## Features

*   **Complex Expression Support**: Solves puzzles with multiple operators, including addition (`+`), subtraction (`-`), multiplication (`*`), division (`/`), and exponentiation (`^`), respecting mathematical precedence.
*   **Finds All Solutions**: Capable of finding and displaying all possible solutions to a puzzle.
*   **Arbitrary Base Support**: Solves puzzles in different numerical bases, from base 2 to base 36.
*   **Constraints**: Allows users to provide constraints by pre-assigning digits to specific letters (e.g., `M=1`).
*   **Powerful Backend**: Utilizes Google's OR-Tools (CP-SAT solver) to efficiently model and solve complex puzzles as constraint satisfaction problems.
*   **AST-Based Parsing**: Safely parses puzzle strings into an Abstract Syntax Tree (AST), allowing for the evaluation of nested expressions without using `eval()`.

## How to Run

1.  Ensure you have Python 3 installed.
2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the main script from your terminal:
    ```bash
    python main.py
    ```
4.  Follow the interactive prompts to enter the puzzle, optional constraints, and the base.

### Example Session

```
Enter a cryptarithm puzzle: SEND + MORE = MONEY
Enter constraints (e.g., O=3, R=4), or press Enter for none:
Enter the base (default is 10):
Solving: SEND + MORE = MONEY in base 10 with constraints {}
Solution: 9567 + 1085 = 10652

Solved in 0.0450 seconds.
```

## Examples

This solver can handle a wide variety of puzzles:

*   **Classic Addition**: `SEND + MORE = MONEY` -> `9567 + 1085 = 10652`
*   **Multiplication**: `ABCD * 9 = DCBA` -> `1089 * 9 = 9801`
*   **Division**: `DONALD / GERALD = R` (approximated)
*   **Exponentiation**: `A ** B = C`
*   **Different Bases**: `GREEN - BLUE = ORANGE` in base 16
*   **With Constraints**: `WRONG + WRONG = RIGHT` with `O=3` -> `49306 + 49306 = 98612`

## Project Structure

*   `main.py`: The main entry point for the application. It handles user input and orchestrates the solving process.
*   `parser.py`: Implements a robust parser that converts the puzzle string into an Abstract Syntax Tree (AST), respecting operator precedence.
*   `solver.py`: A simple wrapper that directs the puzzle to the OR-Tools solver.
*   `or_tools_solver.py`: The core of the solver. It uses the Google OR-Tools CP-SAT solver to model the puzzle as a constraint satisfaction problem and find all valid solutions.
*   `test_solver.py`: Contains a suite of unit tests to ensure the correctness of all modules.

## How It Works

The application leverages **Google's OR-Tools**, a powerful suite for solving combinatorial optimization problems. The old approach of brute-force permutation has been replaced with a more intelligent **constraint programming** model.

1.  **Parse to AST**: The puzzle string (e.g., `SEND + MORE = MONEY`) is first parsed by `parser.py` into an Abstract Syntax Tree (AST). This tree structure accurately represents the mathematical operations and their hierarchy, easily handling complex and nested expressions.

2.  **Create a CP-SAT Model**: In `or_tools_solver.py`, a `CpModel` is instantiated. This model will contain all the variables and constraints of our puzzle.

3.  **Define Variables**: Each unique letter in the puzzle is defined as an integer variable, with a domain (possible values) from `0` to `base - 1`.

4.  **Apply Constraints**: The logic of the puzzle is translated into a set of constraints that the solver must satisfy:
    *   **All Different**: All letter variables must be assigned a unique digit.
    *   **No Leading Zeros**: The first letter of any word (e.g., 'S' in `SEND`) cannot be assigned the digit 0.
    *   **User Constraints**: Any constraints provided by the user (e.g., `M=1`) are added to the model.
    *   **The Main Equation**: The AST is traversed to build a single, large mathematical constraint representing the core puzzle equation. The solver handles `+`, `-`, `*`, `/`, and `^` operations by converting them into equivalent forms within the model.

5.  **Solve**: The CP-SAT solver is invoked. It uses sophisticated search algorithms to find all possible assignments for the letter variables that satisfy every single constraint.

6.  **Return Solutions**: A callback function collects all valid solutions found by the solver. These are then formatted into readable strings and presented to the user.