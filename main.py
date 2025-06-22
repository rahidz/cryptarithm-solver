from solver import solve_cryptarithm

def main():
    """
    Main function to run the cryptarithm solver with a custom puzzle.
    """
    puzzle = input("Enter a cryptarithm puzzle: ")
    print(f"Solving: {puzzle}")
    solution = solve_cryptarithm(puzzle)
    print(f"Solution: {solution}\n")

if __name__ == "__main__":
    main()