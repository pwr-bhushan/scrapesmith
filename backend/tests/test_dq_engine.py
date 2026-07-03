"""app DQ engine — all 6 statuses + normalize."""
from app.dq import check_dq, normalize


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


def test_normalize():
    assert normalize("  a   b ") == "a b"
    assert normalize("₹1,49,900", "number") == "149900"
