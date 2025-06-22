import ast
import operator as op

# Supported operators
_operators = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.Mod: op.mod,
}

# Supported comparators
_comparators = {
    ast.Eq: op.eq,
    ast.NotEq: op.ne,
    ast.Lt: op.lt,
    ast.LtE: op.le,
    ast.Gt: op.gt,
    ast.GtE: op.ge,
}

# Allowed function calls
_allowed_functions = {"int": int}


def safe_eval(expr: str) -> bool:
    """
    Safely evaluates a string expression, allowing only simple arithmetic.

    Args:
        expr: The expression string to evaluate.

    Returns:
        The boolean result of the expression. Returns False on any error.
    """
    try:
        tree = ast.parse(expr, mode="eval")
        return _eval_node(tree.body)
    except (
        ValueError,
        SyntaxError,
        TypeError,
        KeyError,
        NameError,
        ZeroDivisionError,
        RecursionError,
    ):
        # Return False on any evaluation error to signal an invalid equation
        return False


def _eval_node(node):
    """
    Recursively evaluates an AST node.
    """
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        operator = _operators.get(type(node.op))
        if operator is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return operator(left, right)

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left)
        # The solver only creates single comparisons like 'a == b'
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise ValueError("Unsupported comparison with multiple operators.")

        right = _eval_node(node.comparators[0])
        comparator = _comparators.get(type(node.ops[0]))
        if comparator is None:
            raise ValueError(f"Unsupported comparator: {type(node.ops[0]).__name__}")
        return comparator(left, right)

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in _allowed_functions:
            func = _allowed_functions[node.func.id]
            args = [_eval_node(arg) for arg in node.args]
            return func(*args)
        raise ValueError(f"Unsupported function call: {getattr(node.func, 'id', 'N/A')}")

    raise ValueError(f"Unsupported node type: {type(node).__name__}")