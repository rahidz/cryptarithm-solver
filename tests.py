# tests.py
from solver import solve_cryptarithm

def test_send_more_money():
    result = solve_cryptarithm("SEND + MORE = MONEY")
    # The solver may produce different but valid mappings.
    # We will check if the result is a valid equation that holds true.
    assert result is not None and len(result) > 0
    assert eval(result[0].replace('=', '=='))

def test_abcd_puzzle():
    result = solve_cryptarithm("ABCD * 9 = DCBA")
    assert "1089 * 9 = 9801" in result

def test_unsolvable():
    assert ["No solution found"] == solve_cryptarithm("THIS + IS = WRONG")

def test_too_many_letters():
    assert ["Invalid puzzle"] == solve_cryptarithm("ABCDEFGHIJK + L = M")