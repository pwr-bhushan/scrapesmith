"""app DQ engine — all 6 statuses + normalize."""
from app.dq import check_dq, normalize
from app.presets import default_dq


def test_empty_required_vs_optional():
    assert check_dq("", {"required": True}) == "empty"
    assert check_dq(None, {"required": True}) == "empty"
    assert check_dq("", {"required": False}) == "ok"


def test_out_of_scope():
    assert check_dq("anything", {"required": True}, in_scope=False) == "out_of_scope"


def test_regex_fail_and_pass():
    assert check_dq("abc", {"regex": r"^\d+$"}) == "regex_fail"
    assert check_dq("123", {"regex": r"^\d+$"}) == "ok"


def test_number_type_and_range():
    dq = {"parses_as": "number", "range": [0, 5]}
    assert check_dq("4.3", dq) == "ok"
    assert check_dq("9", dq) == "range_fail"
    assert check_dq("abc", dq) == "type_fail"


def test_currency_number_with_regex_cleans():
    dq = {"regex": r"[₹$]", "parses_as": "number", "range": [0, None]}
    assert check_dq("₹1,49,900", dq) == "ok"


def test_len_bounds():
    assert check_dq("abcd", {"min_len": 5}) == "range_fail"
    assert check_dq("abcdef", {"max_len": 3}) == "range_fail"


def test_url_type():
    assert check_dq("https://x.com/a", {"parses_as": "url"}) == "ok"
    assert check_dq("not a url", {"parses_as": "url"}) == "type_fail"


def test_price_preset_accepts_real_prices():
    """The shipped price preset must pass the prices it exists to match.

    Regression: its dq block carried no regex, so check_dq took the comma-only cleaning branch
    and float("₹149900") raised — every currency-prefixed price type_failed.
    """
    dq = default_dq("price")
    for good in ("₹1,49,900", "$1,299.00", "149900", "1,49,900", "€89", "72,990 ₹"):
        assert check_dq(good, dq) == "ok", good
    assert check_dq("Only 3 left", dq) == "regex_fail"  # text must not clean down to a number
    assert check_dq("₹", dq) == "regex_fail"  # bare glyph, no digits
    assert check_dq("", dq) == "empty"  # still required


def test_normalize():
    assert normalize("  a   b ") == "a b"
    assert normalize("₹1,49,900", "number") == "149900"
