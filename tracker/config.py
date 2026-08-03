from __future__ import annotations

import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "tour-data.json"
INDEX_FILE = ROOT / "index.html"

API_BASE = "https://api.setlist.fm/rest/1.0"
ARTIST_MBID = "24e1b53c-3085-4581-8472-0b0088d2508c"

TOUR_NAME = "North American Tour 2026"
TOUR_START = dt.date(2026, 7, 25)
ALLOWED_COUNTRIES = {"US", "CA"}
SCHEDULED_SHOWS = 16

# A full A7X headline set on this tour is much longer than the erroneous
# four-song "Statica" entry. This is a safety check, not the primary filter.
MINIMUM_HEADLINE_SET_LENGTH = 8
