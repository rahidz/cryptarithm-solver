"""CLI and local browser workbench launcher."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Exact cryptarithm workbench")
    parser.add_argument("equations", nargs="*", help="Equations (quote each one)")
    parser.add_argument(
        "--file", type=Path, help="Puzzle JSON or newline-separated equations"
    )
    parser.add_argument("--base", type=int)
    parser.add_argument("--assign", action="append", default=[], metavar="A=1")
    parser.add_argument("--mode", choices=["first", "unique", "limit", "all"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--backend", choices=["cp-sat", "z3"])
    parser.add_argument("--json", action="store_true", help="Print structured results")
    parser.add_argument("--serve", action="store_true", help="Start local web UI")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()
    if args.serve:
        import uvicorn

        uvicorn.run("app:app", host="127.0.0.1", port=args.port)
        return
    from solver import solve_puzzle
    from workbench_math import normalize_spec

    spec = {}
    if args.file:
        content = args.file.read_text()
        if args.file.suffix == ".json":
            spec = json.loads(content)
            if "version" in spec:
                if spec["version"] != 1 or not isinstance(spec.get("puzzle"), dict):
                    parser.error("Expected a version 1 workbench puzzle export.")
                spec = spec["puzzle"]
            spec = spec.get("spec", spec)
        else:
            spec = {
                "equations": [line for line in content.splitlines() if line.strip()]
            }
    if args.equations:
        spec["equations"] = args.equations
    if not spec:
        print("Enter equations, one per line; finish with a blank line:")
        equations = []
        while line := input().strip():
            equations.append(line)
        spec = {"equations": equations}
    for name in ["base", "mode", "limit", "timeout", "backend"]:
        value = getattr(args, name)
        if value is not None:
            spec[name] = value
    try:
        assignments = dict(spec.get("assignments", {}))
        for assignment in args.assign:
            letter, value = assignment.split("=")
            assignments[letter.upper()] = int(value)
        spec["assignments"] = assignments
        result = solve_puzzle(normalize_spec(spec))
    except (ValueError, TypeError, KeyError) as exc:
        result = {
            "status": "invalid",
            "message": str(exc),
            "solutions": [],
            "complete": False,
        }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for index, solution in enumerate(result.get("solutions", []), 1):
            print(f"\nSolution {index}")
            print("\n".join(solution["rendered"]))
            print(
                " ".join(
                    f"{letter}={value}"
                    for letter, value in sorted(solution["assignment"].items())
                )
            )
        print(f"\n{result['status']}: {result.get('message', '')}")
        print(
            f"Search complete: {result.get('complete', False)}; unique: {result.get('unique')}"
        )


if __name__ == "__main__":
    main()
