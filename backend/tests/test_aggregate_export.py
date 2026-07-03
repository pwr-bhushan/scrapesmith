"""Per-field rates + CSV/JSON export (pure)."""
import csv
import io

from app.aggregate import field_rates, flagged_ratios
from app.export import csv_rows, json_tree

FIELDS = [
    {"name": "title", "scope": "single"},
    {"name": "price", "scope": "single"},
    {"name": "items", "scope": "list"},
]

RESULTS = [
    {"file": "a.html", "field_status": {"title": "ok", "price": "ok", "items": "ok"},
     "data": {"title": "A", "price": "10", "items": ["1", "2"]}},
    {"file": "b.html", "field_status": {"title": "ok", "price": "empty", "items": "out_of_scope"},
     "data": {"title": "B", "price": None, "items": []}},
]


def test_field_rates():
    rates = field_rates(RESULTS, FIELDS)
    assert rates["price"] == {"failures": 1, "in_scope": 2, "failure_rate": 0.5}
    assert rates["items"]["in_scope"] == 1  # b is out_of_scope
    assert rates["title"]["failure_rate"] == 0.0


def test_flagged_ratios():
    fr = flagged_ratios(RESULTS, FIELDS)
    assert fr[0]["flagged_ratio"] == 0.0  # a all ok
    assert fr[1]["flagged_ratio"] == 0.5  # b: price flagged of {title,price} in scope


def test_csv_one_row_per_list_item_with_keys():
    text = csv_rows(RESULTS, FIELDS)
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0] == ["__file", "__item_index", "title", "price", "items"]
    # a.html has 2 list items -> 2 rows; single-scope title repeats
    a_rows = [r for r in rows if r[0] == "a.html"]
    assert len(a_rows) == 2
    assert a_rows[0][2] == "A" and a_rows[1][2] == "A"  # title repeats
    assert a_rows[0][4] == "1" and a_rows[1][4] == "2"  # list items differ
    # b.html has no list items -> 1 row
    assert len([r for r in rows if r[0] == "b.html"]) == 1


def test_json_tree_nested():
    tree = json_tree(RESULTS)
    assert tree["a.html"]["items"] == ["1", "2"]
    assert tree["b.html"]["price"] is None
