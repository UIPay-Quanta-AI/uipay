from __future__ import annotations

import pytest

from app.core.amount_parser import parse_amount


@pytest.mark.parametrize(
    ("input_text", "expected_amount"),
    [
        ("send 10k to Mum", 10_000),
        ("transfer 10 thousand naira to Dad", 10_000),
        ("send 10 grand to Mum", 10_000),
        ("pay 10 boi for me", 10_000),
        ("send 5k to Mum", 5_000),
        ("transfer 500 hundred naira", 50_000),
        ("send 2 million naira to Mum", 2_000_000),
        # Igbo
        ("puku iri", 10_000),
        ("puku ise", 5_000),
        # Hausa
        ("dubu goma", 10_000),
        ("dubu biyu", 2_000),
        # Yoruba
        ("egberun mewa", 10_000),
        ("egberun meji", 2_000),
        # Bare large numbers
        ("send 5000 naira", 5_000),
        ("transfer ₦15000", 15_000),
        ("send N20000", 20_000),
    ],
)
def test_parse_amount_valid(input_text: str, expected_amount: int) -> None:
    res = parse_amount(input_text)
    assert res.amount == expected_amount
    assert not res.unresolved


def test_parse_amount_ambiguous_bare_number() -> None:
    # Bare number < 100 without currency marker is ambiguous
    res = parse_amount("send 15 to Mum")
    assert res.amount is None
    assert res.ambiguous == 15


def test_parse_amount_account_number_filtered() -> None:
    # Phone / account numbers (leading zero or > 9 digits) are ignored
    res = parse_amount("send money to 08012345678")
    assert res.amount is None

    res_acct = parse_amount("transfer to 0123456789")
    assert res_acct.amount is None


def test_parse_amount_multiple_amounts() -> None:
    # Last mentioned amount wins with a note
    res = parse_amount("send 5k or make it 10k")
    assert res.amount == 10_000
    assert res.note is not None
    assert "multiple amounts mentioned" in res.note
