import time
from solver import solve_cryptarithm

def main():
    """
    Main function to run the cryptarithm solver with a custom puzzle.
    """
    puzzle = input("Enter a cryptarithm puzzle: ")
    base_str = input("Enter the base (default is 10): ")
    
    try:
        base = int(base_str) if base_str else 10
        if not 2 <= base <= 36:
            raise ValueError
    except ValueError:
        print("Invalid base. Please enter an integer between 2 and 36.")
        return

    print(f"Solving: {puzzle} in base {base}")
    start_time = time.time()
    solutions = solve_cryptarithm(puzzle, base)
    end_time = time.time()
    if solutions:
        for solution in solutions:
            print(f"Solution: {solution}")
    else:
        print("No solution found")
    
    print(f"\nSolved in {end_time - start_time:.4f} seconds.")

if __name__ == "__main__":
    main()