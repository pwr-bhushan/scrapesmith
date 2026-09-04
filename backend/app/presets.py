"""Field type preset library (design §8.2 v1 list).

Each preset carries: a text `regex` (tier-2 inference), a default `dq` block (used by the Phase 4 DQ
engine), `synonyms` (tier-3 label proximity), and `itemprop` names (tier-1 structured data).
"""
from __future__ import annotations

# type -> preset
FIELD_PRESETS: dict = {
    "title": {
        "regex": None,
        "dq": {"required": True, "parses_as": "text", "min_len": 1},
        "synonyms": ["title", "name", "product", "heading"],
        "itemprop": ["name", "title"],
    },
    "price": {
        "regex": r"^[₹$€£]\s?[\d,]+(?:\.\d+)?$|^[\d,]+(?:\.\d+)?\s?[₹$€£]$",
        # The dq regex is deliberately looser than the inference regex above: inference must
        # discriminate price from rating/review_count so it demands a currency glyph, but a field
        # already known to be a price may legitimately render bare. It also gates check_dq's
        # aggressive number-cleaning — without a dq regex the glyph survives into float() and
        # every currency-prefixed price type_fails.
        "dq": {
            "required": True,
            "regex": r"^[₹$€£]?\s?[\d,]+(?:\.\d+)?$|^[\d,]+(?:\.\d+)?\s?[₹$€£]$",
            "parses_as": "number",
            "range": [0, None],
        },
        "synonyms": ["price", "cost", "amount", "mrp", "deal"],
        "itemprop": ["price", "lowPrice", "highPrice"],
    },
    "discount_pct": {
        "regex": r"\d+(?:\.\d+)?\s?%",
        "dq": {"required": False, "parses_as": "number", "range": [0, 100]},
        "synonyms": ["discount", "off", "save", "percent"],
        "itemprop": ["discount"],
    },
    "rating": {
        "regex": r"^[0-5](?:\.\d)?$",
        "dq": {"required": False, "parses_as": "number", "range": [0, 5]},
        "synonyms": ["rating", "stars", "score"],
        "itemprop": ["ratingValue"],
    },
    "review_count": {
        "regex": r"[\d,]+\s*(?:reviews?|ratings?)",
        "dq": {"required": False, "parses_as": "number"},
        "synonyms": ["reviews", "ratings", "count"],
        "itemprop": ["reviewCount", "ratingCount"],
    },
    "availability": {
        "regex": r"(?i)\b(in stock|out of stock|available|unavailable|sold out)\b",
        "dq": {"required": False, "parses_as": "text"},
        "synonyms": ["availability", "stock", "status"],
        "itemprop": ["availability"],
    },
    "image": {
        "regex": None,
        "dq": {"required": False, "parses_as": "url"},
        "synonyms": ["image", "photo", "img", "thumbnail"],
        "itemprop": ["image"],
    },
    "url": {
        "regex": r"https?://\S+",
        "dq": {"required": False, "parses_as": "url"},
        "synonyms": ["url", "link", "href"],
        "itemprop": ["url"],
    },
    "date": {
        "regex": r"\d{4}-\d{2}-\d{2}|\d{1,2}\s+\w+\s+\d{4}",
        "dq": {"required": False, "parses_as": "text"},
        "synonyms": ["date", "published", "posted"],
        "itemprop": ["datePublished", "dateModified"],
    },
    "description": {
        "regex": None,
        "dq": {"required": False, "parses_as": "text"},
        "synonyms": ["description", "summary", "details", "about"],
        "itemprop": ["description"],
    },
    "location": {
        "regex": None,
        "dq": {"required": False, "parses_as": "text"},
        "synonyms": ["location", "address", "city", "place"],
        "itemprop": ["address", "location"],
    },
}

PRESET_TYPES = list(FIELD_PRESETS.keys()) + ["custom"]


def default_dq(field_type: str) -> dict:
    preset = FIELD_PRESETS.get(field_type)
    return dict(preset["dq"]) if preset else {"required": False}
