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
MINIMUM_HEADLINE_SET_LENGTH = 8

TOUR_SCHEDULE = [
    {"date": "2026-07-25", "venue": "Thunder Ridge Nature Arena", "city": "Ridgedale", "region": "Missouri"},
    {"date": "2026-07-27", "venue": "Mystic Lake Amphitheater", "city": "Shakopee", "region": "Minnesota"},
    {"date": "2026-07-30", "venue": "Credit Union 1 Amphitheatre", "city": "Tinley Park", "region": "Illinois"},
    {"date": "2026-08-01", "venue": "Hollywood Casino Amphitheatre", "city": "Maryland Heights", "region": "Missouri"},
    {"date": "2026-08-04", "venue": "Pine Knob Music Theatre", "city": "Clarkston", "region": "Michigan"},
    {"date": "2026-08-06", "venue": "RBC Amphitheatre", "city": "Toronto", "region": "Ontario"},
    {"date": "2026-08-08", "venue": "Bell Centre", "city": "Montreal", "region": "Quebec"},
    {"date": "2026-08-10", "venue": "UBS Arena", "city": "Belmont Park", "region": "New York"},
    {"date": "2026-08-12", "venue": "Xfinity Center", "city": "Mansfield", "region": "Massachusetts"},
    {"date": "2026-08-14", "venue": "Freedom Mortgage Pavilion", "city": "Camden", "region": "New Jersey"},
    {"date": "2026-08-16", "venue": "PNC Music Pavilion", "city": "Charlotte", "region": "North Carolina"},
    {"date": "2026-08-18", "venue": "MIDFLORIDA Credit Union Amphitheatre", "city": "Tampa", "region": "Florida"},
    {"date": "2026-08-21", "venue": "Dos Equis Pavilion", "city": "Dallas", "region": "Texas"},
    {"date": "2026-08-23", "venue": "Ball Arena", "city": "Denver", "region": "Colorado"},
    {"date": "2026-08-25", "venue": "Utah First Credit Union Amphitheatre", "city": "West Valley City", "region": "Utah"},
    {"date": "2026-08-27", "venue": "Talking Stick Resort Amphitheatre", "city": "Phoenix", "region": "Arizona"},
]
