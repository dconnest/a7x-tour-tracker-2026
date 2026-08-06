from __future__ import annotations

import datetime as dt
import email.utils
import json
import random
import time
import urllib.error
import urllib.request
from collections import defaultdict
from typing import Any

from .config import (
    ALLOWED_COUNTRIES,
    API_BASE,
    ARTIST_MBID,
    MINIMUM_HEADLINE_SET_LENGTH,
    TOUR_NAME,
    TOUR_START,
)

MAX_RETRIES = 4
DEFAULT_RETRY_SECONDS = 60
MAX_RETRY_SECONDS = 300


def _retry_after_seconds(error: urllib.error.HTTPError, attempt: int) -> int:
    value = error.headers.get("Retry-After", "").strip()

    if value:
        if value.isdigit():
            return min(MAX_RETRY_SECONDS, max(1, int(value)))

        try:
            retry_time = email.utils.parsedate_to_datetime(value)
            now = dt.datetime.now(dt.timezone.utc)
            if retry_time.tzinfo is None:
                retry_time = retry_time.replace(tzinfo=dt.timezone.utc)
            seconds = int((retry_time - now).total_seconds())
            return min(MAX_RETRY_SECONDS, max(1, seconds))
        except (TypeError, ValueError, OverflowError):
            pass

    backoff = DEFAULT_RETRY_SECONDS * (2 ** attempt)
    jitter = random.randint(0, 15)
    return min(MAX_RETRY_SECONDS, backoff + jitter)


def api_get(path: str, api_key: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={
            "Accept": "application/json",
            "X-Api-Key": api_key,
            "User-Agent": "A7XTourTracker/2.1 (unofficial noncommercial fan project)",
        },
    )

    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))

        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt >= MAX_RETRIES:
                raise

            wait_seconds = _retry_after_seconds(error, attempt)
            print(
                f"setlist.fm rate limit reached (HTTP 429). "
                f"Waiting {wait_seconds} seconds before retry "
                f"{attempt + 1}/{MAX_RETRIES}."
            )
            time.sleep(wait_seconds)

    raise RuntimeError("API retry loop ended unexpectedly.")


def parse_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%d-%m-%Y").date()


def flatten_setlist(item: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    songs: list[dict[str, Any]] = []
    tape_tracks: list[str] = []

    for set_group in item.get("sets", {}).get("set", []):
        set_name = (set_group.get("name") or "").strip()
        encore = set_group.get("encore")

        for song in set_group.get("song", []):
            name = (song.get("name") or "").strip()
            if not name:
                continue

            if song.get("tape"):
                tape_tracks.append(name)
                continue

            songs.append(
                {
                    "name": name,
                    "info": (song.get("info") or "").strip(),
                    "set_name": set_name,
                    "encore": encore,
                    "cover_artist": ((song.get("cover") or {}).get("name") or "").strip(),
                }
            )

    return songs, tape_tracks


def normalize(item: dict[str, Any]) -> dict[str, Any] | None:
    try:
        event_date = parse_date(item["eventDate"])
    except (KeyError, ValueError):
        return None

    venue = item.get("venue") or {}
    city = venue.get("city") or {}
    country = city.get("country") or {}
    country_code = (country.get("code") or "").upper()
    tour_name = ((item.get("tour") or {}).get("name") or "").strip()

    if event_date < TOUR_START or country_code not in ALLOWED_COUNTRIES:
        return None

    songs, tape_tracks = flatten_setlist(item)
    if not songs:
        return None

    return {
        "setlist_id": item.get("id", ""),
        "version_id": item.get("versionId", ""),
        "date": event_date.isoformat(),
        "display_date": event_date.strftime("%B %d, %Y").replace(" 0", " "),
        "venue": venue.get("name") or "Unknown venue",
        "city": city.get("name") or "Unknown city",
        "state": city.get("state") or city.get("stateCode") or "",
        "country": country.get("name") or country_code,
        "country_code": country_code,
        "url": item.get("url") or "",
        "tour_name": tour_name,
        "songs": songs,
        "tape_tracks": tape_tracks,
        "last_updated": item.get("lastUpdated") or "",
    }


def _candidate_score(show: dict[str, Any]) -> tuple[int, int, str]:
    exact_tour = int(show["tour_name"].casefold() == TOUR_NAME.casefold())
    return exact_tour, len(show["songs"]), show.get("last_updated", "")


def select_best_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for show in candidates:
        by_date[show["date"]].append(show)

    selected: list[dict[str, Any]] = []

    for date, date_candidates in by_date.items():
        exact_tour_candidates = [
            show for show in date_candidates
            if show["tour_name"].casefold() == TOUR_NAME.casefold()
        ]

        pool = exact_tour_candidates or date_candidates
        best = max(pool, key=_candidate_score)

        if (
            len(best["songs"]) < MINIMUM_HEADLINE_SET_LENGTH
            and best["tour_name"].casefold() != TOUR_NAME.casefold()
        ):
            print(
                f"Skipping short non-tour entry on {date}: "
                f'{best["tour_name"]!r}, {len(best["songs"])} songs.'
            )
            continue

        selected.append(best)

    return sorted(selected, key=lambda show: (show["date"], show["venue"]))


def fetch_shows(api_key: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    candidates: list[dict[str, Any]] = []
    pages_read = 0

    for page in range(1, 7):
        payload = api_get(f"/artist/{ARTIST_MBID}/setlists?p={page}", api_key)
        items = payload.get("setlist", [])
        if not items:
            break

        pages_read += 1
        page_dates: list[dt.date] = []

        for item in items:
            try:
                page_dates.append(parse_date(item["eventDate"]))
            except (KeyError, ValueError):
                pass

            normalized = normalize(item)
            if normalized:
                candidates.append(normalized)

        if page_dates and max(page_dates) < TOUR_START:
            break

    shows = select_best_candidates(candidates)

    for number, show in enumerate(shows, start=1):
        show["number"] = number

    diagnostics = {
        "pages_read": pages_read,
        "raw_candidates": len(candidates),
        "selected_shows": len(shows),
        "discarded_candidates": max(0, len(candidates) - len(shows)),
    }
    return shows, diagnostics
