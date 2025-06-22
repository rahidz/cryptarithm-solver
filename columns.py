from dataclasses import dataclass, field
from typing import List, Dict, Union, Set
from parser import Operation, Word, Number

@dataclass
class Column:
    addends: List[str]
    result: str
    carry_in: bool

@dataclass
class ColumnEngine:
    ast: Operation
    _columns: List[Column] = field(init=False, default_factory=list)
    _all_letters: Set[str] = field(init=False, default_factory=set)
    _first_letters: Set[str] = field(init=False, default_factory=set)

    def __post_init__(self):
        self._collect_letters(self.ast)
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
        
        left_op = self.ast.left
        result_expr = self.ast.right

        if not isinstance(left_op, Operation) or not isinstance(result_expr, Word):
            # For now, we only support simple `A + B = C` style additions for columnizing
            # The generic solver will handle the rest. This check makes it compatible.
            return

        if left_op.op == '+':
            addend1 = left_op.left
            addend2 = left_op.right
            
            if not isinstance(addend1, Word) or not isinstance(addend2, Word):
                return
                
            max_len = max(len(addend1.letters), len(addend2.letters), len(result_expr.letters))

            for i in range(max_len):
                addends = []
                col_idx1 = len(addend1.letters) - 1 - i
                col_idx2 = len(addend2.letters) - 1 - i
                res_idx = len(result_expr.letters) - 1 - i

                if col_idx1 >= 0:
                    addends.append(addend1.letters[col_idx1])
                if col_idx2 >= 0:
                    addends.append(addend2.letters[col_idx2])
                
                result_char = result_expr.letters[res_idx] if res_idx >= 0 else None
                
                if not result_char:
                    # This implies the result is shorter than the addends, which is unusual
                    # but we'll create a column that expects a carry-out.
                    result_char = f"__carry_{i}"
                    self._all_letters.add(result_char)

                self._columns.append(
                    Column(addends=addends, result=result_char, carry_in=(i > 0))
                )

    def solve(self, base=10, constraints=None):
        # This is a placeholder for the new backtracking solver
        # that will use the generated columns.
        # For now, we'll return a message indicating it's not implemented.
        return ["Column-based solver not yet implemented."]

    @property
    def all_letters(self) -> List[str]:
        return sorted(list(self._all_letters))

    @property
    def first_letters(self) -> Set[str]:
        return self._first_letters