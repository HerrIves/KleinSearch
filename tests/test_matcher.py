import pytest

from matcher import compile_criterion, first_excluded, is_valid_criterion, matches, split_criteria


@pytest.mark.parametrize(
    "text",
    ["MacBook 32GB RAM", "MacBook 32 GB RAM", "32-gb ram", "Arbeitsspeicher: 32 Gb"],
)
def test_units_match_with_or_without_space(text):
    assert matches(text, "32gb")


@pytest.mark.parametrize("text", ["132GB", "32GBit", "M12 chip", "Produkt"])
def test_whole_tokens_only(text):
    assert not matches(text, "32gb")
    assert not matches(text, "m1")
    assert not matches(text, "pro")


def test_alternatives():
    assert matches("Apple MacBook M1 Max 64GB", "m1 pro|m1 max")
    assert matches("Apple MacBook M1Pro", "m1 pro|m1 max")
    assert not matches("Apple MacBook M1 2020", "m1 pro|m1 max")


def test_umlauts_and_case():
    assert matches("Gerät in TOP Zustand", "gerät")
    assert matches("GERÄT", "gerät")


def test_regex_prefix():
    assert matches("i7-8650U", r"re:i[57]-\d{4}")
    assert not is_valid_criterion("re:([")  # invalid regex is ignored, not a crash


def test_empty_criterion_is_invalid():
    assert compile_criterion("   ") is None
    assert not matches("anything", "")


def test_split_criteria_keeps_order():
    matched, missing = split_criteria("MacBook M1 Pro 16GB", ["m1 pro|m1 max", "32gb", "macbook"])
    assert matched == ["m1 pro|m1 max", "macbook"]
    assert missing == ["32gb"]


def test_first_excluded():
    assert first_excluded("Display defekt, sonst ok", ["icloud", "defekt"]) == "defekt"
    assert first_excluded("alles gut", ["icloud", "defekt"]) is None
