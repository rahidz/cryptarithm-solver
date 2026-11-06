from copy import deepcopy

import pytest

from research import certificate, parametric, verify_certificate


def test_parametric_identity():
    result = parametric(
        {"equations": ["AB+BA=(A+B)*11"], "assignments": {"A": 1, "B": 2}}
    )
    assert result["identity"]
    assert result["minimum_base"] == 3
    assert all(row["satisfies"] for row in result["rows"] if row["base"] >= 3)


def test_parametric_finite_root():
    result = parametric({"equations": ["10=2+3"], "assignments": {}})
    assert not result["identity"]
    assert [row["base"] for row in result["rows"] if row["satisfies"]] == [5]


def test_parametric_preserves_cancelled_denominator():
    result = parametric({"equations": ["(10-3)/(10-3)=1"]})
    assert result["identity"]
    assert result["denominator_conditions"] == ["base - 3 != 0"]
    assert not next(row for row in result["rows"] if row["base"] == 3)["defined"]


def test_parametric_zero_denominator_and_legality():
    result = parametric({"equations": ["1/(A-A)=1"], "assignments": {"A": 1}})
    assert not any(row["defined"] for row in result["rows"])
    assert not result["identity"]
    with pytest.raises(ValueError, match="Fix every"):
        parametric({"equations": ["A=A"]})
    with pytest.raises(ValueError, match="distinctness"):
        parametric({"equations": ["A=B"], "assignments": {"A": 1, "B": 1}})


def test_parametric_complexity_limit():
    with pytest.raises(ValueError, match="degree 128"):
        parametric({"equations": ["(10^8)^8*(10^8)^8*10=1"]})


def test_certificate_unique_and_tampering():
    result = certificate({"equations": ["A+1=2"], "base": 3})
    evidence = result["certificate"]
    assert result["complete"]
    assert evidence["solutions"] == [{"A": 1}]
    assert result["verification"]["unique"]
    tampered = deepcopy(evidence)
    tampered["solutions"] = []
    assert not verify_certificate(tampered)["valid"]
    tampered["solutions"] = [{"A": True}]
    assert not verify_certificate(tampered)["valid"]


def test_certificate_negative_arithmetic_and_distinctness():
    spec = {"equations": ["-(A-B)*2=B-A"], "base": 4, "distinct": False}
    result = certificate(spec)
    assert len(result["certificate"]["solutions"]) == 4
    assert result["complete"]
    spec["distinct"] = True
    result = certificate(spec)
    assert result["certificate"]["solutions"] == []
    assert result["verification"]["complete"]


def test_certificate_bounds_and_grammar():
    for spec in [
        {"equations": ["A/A=1"]},
        {"equations": ["ABCDEFG=ABCDEFG"]},
        {"equations": ["ABCDEF=ABCDEF"], "distinct": False},
        {"equations": ["A=A"], "constraints": [{"kind": "prime", "expr": "A"}]},
    ]:
        with pytest.raises(ValueError):
            certificate(spec)


def test_certificate_leading_zero_and_domains():
    result = certificate({"equations": ["AB=B"], "base": 3})
    assert result["certificate"]["solutions"] == []
    result = certificate({"equations": ["A+A=2"], "base": 3, "domains": {"A": [0, 2]}})
    assert result["certificate"]["solutions"] == []
