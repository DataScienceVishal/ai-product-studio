import pytest

from packs import base_amount, cost_per_base, packs_equivalent, parse_pack


@pytest.mark.parametrize("text,expected", [
    ("12x1L", ("ml", 12000)), ("6x400g", ("g", 2400)), ("5kg case", ("g", 5000)), ("6 x 2.5kg", ("g", 15000)),
    ("24x330ml", ("ml", 7920)), ("dozen", ("each", 12)), ("180", ("each", 180)), ("10pk", ("each", 10)),
    ("75cl", ("ml", 750)), ("20L", ("ml", 20000)), ("each", None), ("", None),
])
def test_parse_pack(text, expected):
    assert parse_pack(text) == expected


def test_measure_unit_ignores_pack_text():
    assert base_amount("", "kg") == ("g", 1000)
    assert base_amount("5kg", "kg") == ("g", 1000)  # priced per kg, whatever the pack says


def test_cost_per_base_forms_agree():
    assert packs_equivalent((38.50, "5kg", "pack"), (7.70, "", "kg"))  # a 5kg pack at 38.50 is 7.70 per kg
    kind, cost = cost_per_base(12.0, "12x1L", "case")
    assert kind == "ml" and cost == pytest.approx(0.001)


def test_half_percent_tolerance():
    assert packs_equivalent((10.0, "1kg", "each"), (10.04, "1kg", "each"))
    assert not packs_equivalent((10.0, "1kg", "each"), (10.06, "1kg", "each"))


def test_wrong_pack_is_detected():
    assert not packs_equivalent((24.0, "12x1L", "case"), (24.0, "6x1L", "case"))
    assert not packs_equivalent((24.0, "12x1L", "case"), (24.0, "", "each"))  # ml versus each
