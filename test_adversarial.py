"""Small independent arithmetic checks for corner cases, not backend agreement."""
from fractions import Fraction
from itertools import product

from solver import solve_puzzle


def assignments(result, names):
    assert result['complete'], result
    assert result['status'] in {'satisfiable', 'unsatisfiable'}, result
    return {tuple(solution['assignment'][name] for name in names)
            for solution in result['solutions']}


def test_nested_division_and_negative_denominators():
    expected = set()
    for a, b, c, d in product(range(4), repeat=4):
        if b != c and Fraction(a, b-c) == d:
            expected.add((a, b, c, d))
    actual = solve_puzzle({'equations': ['A/(B-C)=D'], 'base': 4,
                           'distinct': False, 'mode': 'all'})
    assert assignments(actual, 'ABCD') == expected


def test_nested_fraction_has_all_denominator_restrictions():
    expected = set()
    for a, b, c, d in product(range(4), repeat=4):
        if b and c and d and Fraction(a, b)/Fraction(c, d) == 1:
            expected.add((a, b, c, d))
    actual = solve_puzzle({'equations': ['(A/B)/(C/D)=1'], 'base': 4,
                           'distinct': False, 'mode': 'all'})
    assert assignments(actual, 'ABCD') == expected


def test_zero_power_does_not_erase_division_by_zero():
    actual = solve_puzzle({'equations': ['(A/B)^0=1'], 'base': 3,
                           'distinct': False, 'mode': 'all'})
    assert assignments(actual, 'AB') == {(a, b) for a, b in product(range(3), repeat=2) if b}


def test_negative_euclidean_modulus():
    actual = solve_puzzle({'equations': ['A=A', 'B=B'], 'base': 5,
                           'distinct': False, 'mode': 'all',
                           'constraints': [{'kind': 'modular', 'expr': 'A-B',
                                            'modulus': 3, 'remainder': 2}]})
    assert assignments(actual, 'AB') == {(a, b) for a, b in product(range(5), repeat=2)
                                         if (a-b) % 3 == 2}


def test_expression_remainder_is_resolved_in_checker():
    actual = solve_puzzle({'equations': ['A=A'], 'mode': 'all',
                           'constraints': [{'kind': 'modular', 'expr': 'A',
                                            'modulus': 3, 'remainder': '1'}]})
    assert assignments(actual, 'A') == {(1,), (4,), (7,)}


def test_anonymous_constraint_cells_do_not_alias_equation_cells():
    actual = solve_puzzle({'equations': ['?=0'], 'mode': 'unique',
                           'constraints': [{'kind': 'inequality', 'expr': '?',
                                            'op': '=', 'value': 1}]})
    # Raw blanks in predicates are rejected rather than silently bound to ?1.
    assert actual['status'] == 'invalid', actual
    assert 'explicit anonymous' in actual['message']
    assert not actual['complete']


def test_empty_intersected_domain_is_unsat_not_unique():
    actual = solve_puzzle({'equations': ['AA=AA'], 'mode': 'unique',
                           'domains': {'A': [0]}})
    assert actual['status'] == 'unsatisfiable', actual
    assert actual['complete'] is True
    assert actual['unique'] is not True


def test_signed_column_carries_match_integer_arithmetic():
    expected = {(a, b, c, d, e) for a, b, c, d, e in product(range(4), repeat=5)
                if b and d and a-(4*b+c) == -(4*d+e)}
    actual = solve_puzzle({'equations': ['A-BC=-DE'], 'base': 4,
                           'distinct': False, 'mode': 'all'})
    assert assignments(actual, 'ABCDE') == expected


def test_column_model_does_not_truncate_large_numerals():
    actual = solve_puzzle({'equations': ['99999999999999999999+A=100000000000000000000'],
                           'mode': 'unique'})
    assert actual['status'] == 'satisfiable', actual
    assert actual['unique'] is True
    assert actual['solutions'][0]['assignment'] == {'A': 1}
