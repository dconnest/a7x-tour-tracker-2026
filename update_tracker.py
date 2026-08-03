from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.error

from tracker.config import (
    ARTIST_MBID,
    DATA_FILE,
    INDEX_FILE,
    SCHEDULED_SHOWS,
    TOUR_NAME,
    TOUR_START,
    ALLOWED_COUNTRIES,
)
from tracker.fetch import fetch_shows
from tracker.render import render_site
from tracker.stats import build_song_stats, enrich_shows


def main() -> int:
    api_key = os.environ.get("SETLIST_FM_API_KEY", "").strip()
    if not api_key:
        print("ERROR: SETLIST_FM_API_KEY is missing.", file=sys.stderr)
        return 2

    try:
        shows, diagnostics = fetch_shows(api_key)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"ERROR: setlist.fm request failed: {exc}", file=sys.stderr)
        return 1

    enrich_shows(shows)
    song_stats = build_song_stats(shows)

    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    payload = {
        "generated_at": generated_at,
        "artist": {"name": "Avenged Sevenfold", "mbid": ARTIST_MBID},
        "tour": {
            "name": TOUR_NAME,
            "start_date": TOUR_START.isoformat(),
            "countries": sorted(ALLOWED_COUNTRIES),
            "scheduled_shows": SCHEDULED_SHOWS,
        },
        "shows": shows,
        "song_stats": song_stats,
        "diagnostics": diagnostics,
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    INDEX_FILE.write_text(render_site(payload), encoding="utf-8")

    print("A7X tracker update complete")
    print(f"  API pages read:          {diagnostics['pages_read']}")
    print(f"  Candidate setlists:      {diagnostics['raw_candidates']}")
    print(f"  Discarded duplicates:    {diagnostics['discarded_candidates']}")
    print(f"  Selected tour shows:     {diagnostics['selected_shows']}")
    print(f"  Unique tour songs:       {len(song_stats)}")
    if shows:
        print(
            f"  Latest selected show:    #{shows[-1]['number']} "
            f"{shows[-1]['date']} — {shows[-1]['venue']}"
        )
    print(f"  Generated:               {INDEX_FILE.name}, {DATA_FILE.relative_to(DATA_FILE.parent.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
