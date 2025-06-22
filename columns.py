from dataclasses import dataclass, field
from itertools import permutations
from typing import List, Dict, Union, Set

from parser import Operation, Word, Number


def _to_base_char(n):
    if n < 10:
        return str(n)
    return chr(ord('A') + n - 10)

@dataclass
class Column:
    addends: List[str]
    result: str
    carry_in: bool
    is_carry_out: bool = False

@dataclass
class ColumnEngine:
    ast: Operation
    _columns: List[Column] = field(init=False, default_factory=list)
    _all_letters: Set[str] = field(init=False, default_factory=set)
    _first_letters: Set[str] = field(init=False, default_factory=set)

    def __post_init__(self):
        # We need to collect letters from the entire AST, including the result.
        def _collect_all_letters(node: Union[Operation, Word, Number]):
            if isinstance(node, Word):
                self._all_letters.update(node.letters)
                if node.letters:
                    self._first_letters.add(node.letters[0])
            elif isinstance(node, Operation):
                _collect_all_letters(node.left)
                _collect_all_letters(node.right)
        
        _collect_all_letters(self.ast)
        self._build_columns()

    def _collect_letters(self, node: Union[Operation, Word, Number]):
        if isinstance(node, Word):
            self._all_letters.update(node.letters)
            if node.letters:
                self._first_letters.add(node.letters[0])
        elif isinstance(node, Operation):
            self._collect_letters(node.left)
            self._collect_letters(node.right)

    def _build_columns(self):
        if self.ast.op != '=':
            raise ValueError("AST root must be an equality.")

        result_expr = self.ast.right
        if not isinstance(result_expr, Word):
            return  # Column engine only supports Word results for now

        addend_nodes = []
        def collect_addends(node):
            if isinstance(node, Operation) and node.op == '+':
                collect_addends(node.left)
                collect_addends(node.right)
            elif isinstance(node, Word):
                addend_nodes.append(node)
            else:
                # If any part of the sum is not a Word, we can't use the column engine.
                raise TypeError("Invalid node type in addition chain.")

        try:
            collect_addends(self.ast.left)
        except TypeError:
            return # Fallback to generic solver if the structure is not a simple sum of words.

        max_len = max(len(n.letters) for n in addend_nodes + [result_expr])

        for i in range(max_len):
            col_addends = []
            for addend in addend_nodes:
                col_idx = len(addend.letters) - 1 - i
                if col_idx >= 0:
                    col_addends.append(addend.letters[col_idx])
            
            res_idx = len(result_expr.letters) - 1 - i
            is_carry_out_col = res_idx < 0
            if is_carry_out_col:
                result_char = ''
            else:
                result_char = result_expr.letters[res_idx]

            self._columns.append(
                Column(addends=col_addends, result=result_char, carry_in=(i > 0), is_carry_out=is_carry_out_col)
            )

    def solve(self, puzzle_string: str, base=10, constraints=None):
        if constraints is None:
            constraints = {}

        solutions = []

        def backtrack(col_idx, carry, mapping):
            if col_idx >= len(self._columns):
                if carry == 0:
                    # All columns are solved, construct the solution string
                    solution_str = puzzle_string.upper()
                    for letter, digit in mapping.items():
                        solution_str = solution_str.replace(letter, _to_base_char(digit))
                    solutions.append(solution_str)
                return

            column = self._columns[col_idx]

            current_col_letters = set(column.addends)
            if not column.is_carry_out:
                current_col_letters.add(column.result)

            unassigned_letters = sorted([l for l in current_col_letters if l not in mapping])
            available_digits = [d for d in range(base) if d not in mapping.values()]

            for p in permutations(available_digits, len(unassigned_letters)):
                temp_mapping = dict(zip(unassigned_letters, p))

                if any(temp_mapping.get(l) == 0 and l in self.first_letters for l in unassigned_letters):
                    continue

                full_col_mapping = mapping.copy()
                full_col_mapping.update(temp_mapping)

                try:
                    col_sum = sum(full_col_mapping[l] for l in column.addends) + carry
                    
                    if column.is_carry_out:
                        # This is a carry-out column. The result of this column must be 0.
                        if col_sum % base == 0:
                            new_carry = col_sum // base
                            backtrack(col_idx + 1, new_carry, full_col_mapping)
                    else:
                        result_digit = full_col_mapping[column.result]
                        if col_sum % base == result_digit:
                            new_carry = col_sum // base
                            backtrack(col_idx + 1, new_carry, full_col_mapping)

                except KeyError:
                    # A letter in the column is not yet mapped.
                    continue
        
        # Initial call to start the backtracking from the first column (rightmost)
        backtrack(0, 0, constraints.copy())

        if not solutions:
            return ["No solution found"]
        return sorted(list(set(solutions)))

    @property
    def all_letters(self) -> List[str]:
        return sorted(list(self._all_letters))

    @property
    def first_letters(self) -> Set[str]:
        return self._first_letters