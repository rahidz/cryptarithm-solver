# Cryptarithm Solver

This project is a Python application designed to solve cryptarithmetic puzzles.

## Plan: A Modular Approach

The application is structured into several modules to ensure scalability, extensibility, and maintainability. This design supports future enhancements such as adding a graphical user interface (GUI) or incorporating new types of puzzles.

### File Structure

*   `main.py`: The main entry point for the application. It will handle orchestrating the parsing and solving process. In the future, it can be extended to manage command-line arguments or launch a GUI.
*   `parser.py`: Contains the logic for parsing the puzzle string (e.g., `"SEND + MORE = MONEY"`). It transforms the raw string into a structured format that the solver can process, extracting the words and unique letters.
*   `solver.py`: Houses the core puzzle-solving logic. It takes the structured data from the parser and uses a brute-force permutation algorithm to find a valid mapping of letters to digits.
*   `tests.py`: Contains unit tests for all modules to ensure correctness.

### High-Level Flow

The diagram below illustrates how the different modules interact:

```mermaid
graph TD
    subgraph main.py
        A[Start Application] --> B[Get puzzle string];
    end

    subgraph parser.py
        C[parse_puzzle(string)] --> D{Return parsed data (words, letters)};
    end

    subgraph solver.py
        E[solve(parsed_data)] --> F{Generate & Test Permutations};
        F -- Solution Found --> G[Return formatted solution];
        F -- No Solution --> H[Return "No solution found"];
    end

    B --> C;
    D --> E;
    G --> I[Display Solution];
    H --> I;
    A --> I;
```

### Core Solving Algorithm

1.  **Parse the Puzzle**: The `parser.py` module will validate the puzzle string and extract all unique letters and words. It will raise an error if the puzzle contains more than 10 unique letters.
2.  **Generate Permutations**: The `solver.py` module will generate all possible permutations of the digits 0-9 for the set of unique letters.
3.  **Test Each Permutation**: For each permutation, the solver will:
    *   Create a mapping from letters to digits.
    *   Check for leading zeros (e.g., the first letter of a word cannot be '0'). Invalid mappings are discarded.
    *   Substitute the letters in the puzzle with their assigned digits to form a numerical equation.
    *   Evaluate the equation.
4.  **Return the Result**:
    *   If a valid solution is found, it is formatted and returned.
    *   If all permutations are tested and no solution is found, a "No solution found" message is returned.