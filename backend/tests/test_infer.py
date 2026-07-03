"""Inference cascade + /infer route (no DB, no model needed)."""
from httpx import ASGITransport, AsyncClient

from app.infer import classify_with_llm, infer_type
from app.main import app


def test_itemprop_wins_structured():
    r = infer_type(text="₹1,49,900", itemprop="price")
    assert r["type"] == "price" and r["source"] == "structured" and r["confidence"] == 0.95
    assert r["dq"]["parses_as"] == "number"


def test_regex_price_and_percent():
    assert infer_type(text="₹1,49,900")["type"] == "price"
    assert infer_type(text="6% off")["type"] == "discount_pct"
    assert infer_type(text="4.3")["type"] == "rating"
    assert infer_type(text="12,341 reviews")["type"] == "review_count"
    assert infer_type(text="In stock")["type"] == "availability"


def test_label_proximity():
    r = infer_type(text="1099", label="Cost:")
    assert r["type"] == "price" and r["source"] == "label"


def test_no_signal():
    r = infer_type(text="lorem ipsum dolor")
    assert r["type"] is None and r["source"] == "none"


def test_llm_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = classify_with_llm("something")
    assert r["source"] == "llm_unavailable" and r["type"] is None


async def test_infer_route():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post("/infer", json={"text": "₹1,49,900", "itemprop": "price"})
        assert r.json()["type"] == "price"
        p = await c.get("/presets")
        assert "price" in p.json()["types"] and "custom" in p.json()["types"]
