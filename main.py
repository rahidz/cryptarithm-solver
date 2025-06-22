import time
from solver import solve_cryptarithm

def main():
    """
    Main function to run the cryptarithm solver with a custom puzzle.
    """
    print("Enter the cryptarithm equations, one per line.")
    print("The last line of the puzzle should be the final sum.")
    print("Press Enter on an empty line when you are finished.")
    
    puzzles = []
    while True:
        line = input()
        if not line:
            break
        puzzles.append(line)

    if not puzzles:
        print("No puzzle entered.")
        return

    constraints_str = input("Enter constraints (e.g., O=3, R=4), or press Enter for none: ")
    base_str = input("Enter the base (default is 10): ")

    constraints = {}
    if constraints_str:
        try:
            for part in constraints_str.split(','):
                letter, digit = part.strip().split('=')
                constraints[letter.upper()] = int(digit)
        except (ValueError, IndexError):
            print("Invalid constraints format. Please use 'L=D, L=D'. Example: O=3, R=4")
            return

    try:
        base = int(base_str) if base_str else 10
        if not 2 <= base <= 36:
            raise ValueError
    except ValueError:
        print("Invalid base. Please enter an integer between 2 and 36.")
        return

    print(f"Solving: {puzzles} in base {base} with constraints {constraints}")
    start_time = time.time()
    solutions = solve_cryptarithm(puzzles, base, constraints)
    end_time = time.time()
    if solutions:
        for i, solution in enumerate(solutions):
            print(f"--- Solution {i+1} ---")
            print(solution)
            print("-" * (len(f"--- Solution {i+1} ---")))
    else:
        print("No solution found")
    
    print(f"\nSolved in {end_time - start_time:.4f} seconds.")

if __name__ == "__main__":
    main()