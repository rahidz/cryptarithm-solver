import time
from solver import solve_cryptarithm

def main():
    """
    Main function to run the cryptarithm solver with a custom puzzle.
    """
    puzzle = input("Enter a cryptarithm puzzle: ")
    print(f"Solving: {puzzle}")
    start_time = time.time()
    solutions = solve_cryptarithm(puzzle)
    end_time = time.time()
    if solutions:
        for solution in solutions:
            print(f"Solution: {solution}")
    else:
        print("No solution found")
    
    print(f"\nSolved in {end_time - start_time:.4f} seconds.")

if __name__ == "__main__":
    main()