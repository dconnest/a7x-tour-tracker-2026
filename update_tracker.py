#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import html
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data" / "tour-data.json"
INDEX_FILE = ROOT / "index.html"

API_BASE = "https://api.setlist.fm/rest/1.0"
ARTIST_MBID = "24e1b53c-3085-4581-8472-0b0088d2508c"
TOUR_START = dt.date(2026, 7, 25)
ALLOWED_COUNTRIES = {"US", "CA"}
SCHEDULED_SHOWS = 16


def api_get(path: str, api_key: str) -> dict:
    request = urllib.request.Request(
        API_BASE + path,
        headers={
            "Accept": "application/json",
            "X-Api-Key": api_key,
            "User-Agent": "A7XTourTracker/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_date(value: str) -> dt.date:
    return dt.datetime.strptime(value, "%d-%m-%Y").date()


def flatten_setlist(item: dict) -> tuple[list[dict], list[str]]:
    songs = []
    tape_tracks = []

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


def normalize(item: dict) -> dict | None:
    try:
        event_date = parse_date(item["eventDate"])
    except (KeyError, ValueError):
        return None

    venue = item.get("venue") or {}
    city = venue.get("city") or {}
    country = city.get("country") or {}
    country_code = (country.get("code") or "").upper()

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
        "tour_name": ((item.get("tour") or {}).get("name") or "").strip(),
        "songs": songs,
        "tape_tracks": tape_tracks,
        "last_updated": item.get("lastUpdated") or "",
    }


def fetch_shows(api_key: str) -> list[dict]:
    collected = {}

    for page in range(1, 7):
        payload = api_get(f"/artist/{ARTIST_MBID}/setlists?p={page}", api_key)
        items = payload.get("setlist", [])
        if not items:
            break

        dates = []
        for item in items:
            try:
                dates.append(parse_date(item["eventDate"]))
            except Exception:
                pass

            show = normalize(item)
            if show:
                key = (show["date"], show["venue"])
                if key not in collected:
                    collected[key] = show

        if dates and max(dates) < TOUR_START:
            break

    shows = sorted(collected.values(), key=lambda s: (s["date"], s["venue"]))
    for i, show in enumerate(shows, start=1):
        show["number"] = i
    return shows


def names(show: dict) -> list[str]:
    return [song["name"] for song in show["songs"]]


def similarity(a: list[str], b: list[str]) -> int:
    left, right = set(a), set(b)
    union = left | right
    return round(100 * len(left & right) / len(union)) if union else 100


def enrich(shows: list[dict]) -> None:
    seen = set()

    for i, show in enumerate(shows):
        current = names(show)
        previous = names(shows[i - 1]) if i else []

        show["opener"] = current[0]
        show["closer"] = current[-1]
        show["set_length"] = len(current)
        show["tour_debuts"] = [song for song in current if song not in seen]
        show["live_debuts"] = [
            song["name"]
            for song in show["songs"]
            if "live debut" in song.get("info", "").lower()
        ]

        if i:
            show["added"] = [song for song in current if song not in previous]
            show["dropped"] = [song for song in previous if song not in current]
            show["returned"] = [
                song for song in show["added"]
                if any(song in names(old) for old in shows[: i - 1])
            ]
            show["similarity"] = similarity(current, previous)
        else:
            show["added"] = []
            show["dropped"] = []
            show["returned"] = []
            show["similarity"] = None

        seen.update(current)


def build_song_stats(shows: list[dict]) -> list[dict]:
    ordered = []
    for show in shows:
        for song in names(show):
            if song not in ordered:
                ordered.append(song)

    stats = []
    total = len(shows)

    for song in ordered:
        appearances = []
        positions = []
        opener_count = 0
        closer_count = 0

        for show in shows:
            show_names = names(show)
            if song in show_names:
                appearances.append(show["number"])
                positions.append(show_names.index(song) + 1)
                opener_count += int(show_names[0] == song)
                closer_count += int(show_names[-1] == song)

        streak = 0
        for show in reversed(shows):
            if song in names(show):
                streak += 1
            else:
                break

        stats.append(
            {
                "name": song,
                "appearances": len(appearances),
                "rate": round(100 * len(appearances) / total) if total else 0,
                "streak": streak,
                "first_show": min(appearances),
                "last_show": max(appearances),
                "average_position": round(sum(positions) / len(positions), 1),
                "opener_count": opener_count,
                "closer_count": closer_count,
            }
        )

    return sorted(stats, key=lambda s: (-s["appearances"], s["name"].lower()))


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def location(show: dict) -> str:
    region = show.get("state") or show.get("country")
    return f'{show["city"]}, {region}' if region else show["city"]


def render(data: dict) -> str:
    shows = data["shows"]
    song_stats = data["song_stats"]
    latest = shows[-1] if shows else None
    unique_songs = len(song_stats)
    progress = round(100 * len(shows) / SCHEDULED_SHOWS, 1)
    avg_length = round(sum(s["set_length"] for s in shows) / len(shows), 1) if shows else 0

    if latest:
        added = ", ".join(latest["added"]) or "None"
        dropped = ", ".join(latest["dropped"]) or "None"
        returned = ", ".join(latest["returned"]) or "None"
        latest_similarity = f'{latest["similarity"]}%' if latest["similarity"] is not None else "Opening show"
        latest_title = latest["venue"]
        latest_meta = f'{location(latest)} · {latest["display_date"]}'
    else:
        added = dropped = returned = "None"
        latest_similarity = "—"
        latest_title = "Waiting for the first confirmed show"
        latest_meta = "The automatic updater is connected."

    show_cards = ""
    for show in reversed(shows):
        if show["number"] == 1:
            summary = "Opening-night rotation established."
        elif show["added"] or show["dropped"]:
            pieces = []
            if show["added"]:
                pieces.append("Added: " + ", ".join(show["added"]))
            if show["dropped"]:
                pieces.append("Dropped: " + ", ".join(show["dropped"]))
            summary = " · ".join(pieces)
        else:
            summary = "No song changes from the previous tracked show."

        show_cards += f"""
        <article class="showCard">
          <span class="muted">Show #{show["number"]} · {esc(show["display_date"])}</span>
          <h3>{esc(show["venue"])}</h3>
          <p>{esc(location(show))}</p>
          <div class="highlight">{esc(summary)}</div>
          <a class="source" href="{esc(show["url"])}" target="_blank" rel="noopener">Source: setlist.fm ↗</a>
        </article>"""

    latest_setlist = ""
    if latest:
        for position, song in enumerate(latest["songs"], start=1):
            labels = []
            if position == 1:
                labels.append("Opener")
            if position == len(latest["songs"]):
                labels.append("Closer")
            if song["name"] in latest["tour_debuts"]:
                labels.append("Tour debut")
            if song["name"] in latest["live_debuts"]:
                labels.append("Live debut")
            if song.get("encore"):
                labels.append(f'Encore {song["encore"]}')
            if song.get("info"):
                labels.append(song["info"])

            latest_setlist += f"""
            <div class="song" data-song="{esc(song["name"].lower())}">
              <div class="songNum">{position}</div>
              <div>
                <div class="songTitle">{esc(song["name"])}</div>
                <div class="note">{esc(" · ".join(labels) or f'Appearance at Show #{latest["number"]}')}</div>
              </div>
            </div>"""

    song_rows = "".join(
        f"""<div class="songRow"><strong>{esc(song["name"])}</strong>
        <span>{song["appearances"]}</span><span>{song["rate"]}%</span>
        <span>{song["streak"]}</span><span>{song["average_position"]}</span></div>"""
        for song in song_stats
    )

    heat_headers = "".join(
        f'<div class="heatHead">#{show["number"]}</div>' for show in shows
    )
    heat_rows = ""
    for song in song_stats:
        cells = "".join(
            '<div class="heatCell played">✓</div>'
            if song["name"] in names(show)
            else '<div class="heatCell"></div>'
            for show in shows
        )
        heat_rows += f'<div class="heatRow"><span>{esc(song["name"])}</span>{cells}</div>'

    history = ""
    for show in shows:
        if show["number"] == 1:
            narrative = "The tracked North American tour begins."
        elif show["added"] or show["dropped"]:
            pieces = []
            if show["added"]:
                pieces.append("Added: " + ", ".join(show["added"]))
            if show["dropped"]:
                pieces.append("Dropped: " + ", ".join(show["dropped"]))
            narrative = " · ".join(pieces)
        else:
            narrative = "The prior show’s song selection was repeated."

        history += f"""
        <div class="event">
          <div class="eventDate">{esc(dt.date.fromisoformat(show["date"]).strftime("%b %d").upper())}</div>
          <div class="eventBody">
            <strong>{esc(show["venue"])} · {esc(location(show))}</strong>
            <span class="muted">{esc(narrative)}</span>
          </div>
        </div>"""

    heat_columns = max(1, len(shows))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Unofficial Avenged Sevenfold 2026 North American Tour tracker">
<title>A7X Tour Tracker 2026</title>
<style>
:root{{--bg:#07080b;--panel:#12141a;--panel2:#191c24;--line:#2b2f39;--text:#f6f7fb;--muted:#9ca3af;--red:#df252d;--red2:#ff5b63}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:radial-gradient(circle at 85% 0,rgba(223,37,45,.18),transparent 30%),var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}a{{color:inherit;text-decoration:none}}.shell{{width:min(1180px,calc(100% - 34px));margin:auto}}
header{{position:sticky;top:0;z-index:30;background:rgba(7,8,11,.86);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}}.nav{{min-height:72px;display:flex;align-items:center;justify-content:space-between;gap:24px}}.brand{{display:flex;align-items:center;gap:12px;font-weight:900}}.brandMark{{width:42px;height:42px;display:grid;place-items:center;border:1px solid var(--red);border-radius:11px;color:var(--red2);font-size:12px}}nav{{display:flex;gap:20px;color:var(--muted);font-size:14px}}
.hero{{padding:88px 0 48px}}.eyebrow{{text-transform:uppercase;letter-spacing:.18em;font-size:12px;font-weight:900;color:var(--red2)}}h1{{font-size:clamp(48px,8vw,88px);line-height:.94;letter-spacing:-.055em;margin:16px 0 22px}}h1 em{{font-style:normal;color:var(--red2)}}.lede{{max-width:760px;color:var(--muted);font-size:20px;line-height:1.65}}
.section{{padding:34px 0 52px}}.sectionHead{{display:flex;align-items:end;justify-content:space-between;gap:18px;margin-bottom:18px}}.sectionHead h2{{margin:4px 0 0;font-size:34px}}.muted{{color:var(--muted)}}.grid{{display:grid;gap:16px}}.statsGrid{{grid-template-columns:repeat(4,1fr)}}.featureGrid{{grid-template-columns:1.35fr 1fr;margin-top:18px}}.showGrid{{grid-template-columns:repeat(3,1fr)}}.compareGrid{{grid-template-columns:repeat(4,1fr)}}
.panel,.statCard,.showCard{{background:linear-gradient(180deg,rgba(24,27,36,.97),rgba(16,18,24,.97));border:1px solid var(--line);border-radius:18px;padding:22px}}.statCard span,.statCard small{{display:block;color:var(--muted)}}.statCard strong{{display:block;font-size:42px;margin:10px 0 4px}}.feature h2{{font-size:34px;margin:8px 0}}.highlight{{margin-top:22px;padding:15px 16px;border-left:3px solid var(--red);border-radius:10px;background:rgba(223,37,45,.08)}}.source{{display:inline-block;margin-top:14px;color:var(--red2);font-size:13px}}.progress{{height:12px;border-radius:999px;background:#262a34;overflow:hidden;margin:22px 0}}.progress span{{display:block;height:100%;width:{progress}%;background:linear-gradient(90deg,var(--red),var(--red2))}}
.showCard h3{{font-size:22px;margin:10px 0 6px}}.showCard p{{margin:0;color:var(--muted)}}.miniCard{{padding:18px;text-align:center;border:1px solid var(--line);border-radius:16px;background:var(--panel2)}}.miniCard strong{{display:block;font-size:30px;margin-top:6px;overflow-wrap:anywhere}}.search{{width:100%;max-width:280px;padding:11px 13px;border-radius:12px;border:1px solid var(--line);background:#0d0f14;color:#fff}}
.setlist{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}.song{{display:flex;gap:13px;padding:14px 15px;background:var(--panel);border:1px solid var(--line);border-radius:14px}}.songNum{{width:28px;height:28px;display:grid;place-items:center;border-radius:50%;background:rgba(223,37,45,.14);color:#ff8b90;font-size:12px;font-weight:900;flex:none}}.songTitle{{font-weight:800}}.note{{font-size:12px;color:var(--muted);margin-top:4px}}
.songTable{{border:1px solid var(--line);border-radius:18px;overflow:hidden}}.songTableHead,.songRow{{display:grid;grid-template-columns:2fr repeat(4,1fr);gap:12px;padding:16px 20px}}.songTableHead{{background:#20232c;color:var(--muted);font-size:12px;text-transform:uppercase}}.songRow{{background:var(--panel);border-top:1px solid var(--line)}}.heatWrap{{overflow-x:auto}}.heatmap{{min-width:max(760px,calc(220px + {heat_columns} * 72px));display:grid;grid-template-columns:220px repeat({heat_columns},64px);gap:8px;align-items:center}}.heatHead{{font-size:12px;color:var(--muted);text-align:center}}.heatRow{{display:contents}}.heatCell{{height:38px;border-radius:8px;background:#222630;display:grid;place-items:center}}.heatCell.played{{background:var(--red)}}.timeline{{display:grid;gap:14px}}.event{{display:grid;grid-template-columns:100px 1fr;gap:18px}}.eventDate{{font-weight:900;color:var(--red2)}}.eventBody{{border-left:2px solid var(--line);padding:0 0 20px 18px}}footer{{border-top:1px solid var(--line);padding:30px 0 42px;color:var(--muted);font-size:13px}}.hidden{{display:none!important}}
@media(max-width:900px){{nav{{display:none}}.statsGrid,.compareGrid{{grid-template-columns:repeat(2,1fr)}}.featureGrid,.showGrid{{grid-template-columns:1fr}}}}@media(max-width:620px){{.statsGrid,.compareGrid,.setlist{{grid-template-columns:1fr}}.songTableHead{{display:none}}.songRow{{grid-template-columns:1fr 60px 60px}}.songRow span:nth-child(4),.songRow span:nth-child(5){{display:none}}.event{{grid-template-columns:1fr}}.eventBody{{border-left:0;border-top:1px solid var(--line);padding:12px 0 18px}}}}
</style>
</head>
<body>
<header><div class="shell nav"><a class="brand" href="#top"><span class="brandMark">A7X</span><span>Tour Tracker <b>2026</b></span></a><nav><a href="#dashboard">Dashboard</a><a href="#shows">Shows</a><a href="#songs">Songs</a><a href="#heatmap">Heat Map</a><a href="#history">History</a></nav></div></header>
<main id="top">
<section class="hero"><div class="shell"><p class="eyebrow">North American Tour 2026</p><h1>Every show.<br>Every song.<br><em>Every change.</em></h1><p class="lede">Automatically updated from confirmed setlist.fm data.</p></div></section>
<section class="shell section" id="dashboard">
<div class="statsGrid grid"><article class="statCard"><span>Shows completed</span><strong>{len(shows)} / {SCHEDULED_SHOWS}</strong><small>{progress}% of scheduled dates</small></article><article class="statCard"><span>Unique songs</span><strong>{unique_songs}</strong><small>Across tracked shows</small></article><article class="statCard"><span>Average set length</span><strong>{avg_length}</strong><small>Performed songs</small></article><article class="statCard"><span>Latest similarity</span><strong>{latest_similarity}</strong><small>Compared with prior show</small></article></div>
<div class="featureGrid grid"><article class="panel feature"><p class="eyebrow">Latest completed show</p><h2>{esc(latest_title)}</h2><p class="muted">{esc(latest_meta)}</p><div class="highlight"><strong>Latest changes:</strong> Added: {esc(added)} · Dropped: {esc(dropped)} · Returned: {esc(returned)}</div></article><article class="panel"><p class="eyebrow">Tour progress</p><div class="progress"><span></span></div><h3>{len(shows)} of {SCHEDULED_SHOWS} shows complete</h3><p class="muted">The tracker checks daily and republishes only when data changes.</p></article></div>
</section>
<section class="shell section" id="shows"><div class="sectionHead"><div><p class="eyebrow">Tracked shows</p><h2>Completed performances</h2></div></div><div class="showGrid grid">{show_cards or '<div class="panel">No completed setlists have been returned yet.</div>'}</div></section>
<section class="shell section"><div class="sectionHead"><div><p class="eyebrow">Latest comparison</p><h2>What changed?</h2></div></div><div class="compareGrid grid"><div class="miniCard"><span class="muted">Added</span><strong>{esc(added)}</strong></div><div class="miniCard"><span class="muted">Dropped</span><strong>{esc(dropped)}</strong></div><div class="miniCard"><span class="muted">Returned</span><strong>{esc(returned)}</strong></div><div class="miniCard"><span class="muted">Similarity</span><strong>{latest_similarity}</strong></div></div></section>
<section class="shell section"><div class="sectionHead"><div><p class="eyebrow">Latest setlist</p><h2>Running order</h2></div><input id="songSearch" class="search" placeholder="Search songs..."></div><div class="setlist">{latest_setlist or '<div class="panel">Waiting for setlist data.</div>'}</div></section>
<section class="shell section" id="songs"><div class="sectionHead"><div><p class="eyebrow">Song database</p><h2>Current rotation</h2></div></div><div class="songTable"><div class="songTableHead"><span>Song</span><span>Shows</span><span>Rate</span><span>Streak</span><span>Avg. position</span></div>{song_rows}</div></section>
<section class="shell section" id="heatmap"><div class="sectionHead"><div><p class="eyebrow">Heat map</p><h2>Song usage by show</h2></div></div><div class="panel heatWrap"><div class="heatmap"><div></div>{heat_headers}{heat_rows}</div></div></section>
<section class="shell section" id="history"><div class="sectionHead"><div><p class="eyebrow">Tour history</p><h2>The story so far</h2></div></div><div class="panel timeline">{history or '<span class="muted">Waiting for the first completed show.</span>'}</div></section>
</main>
<footer><div class="shell">Unofficial fan project. Not affiliated with Avenged Sevenfold. Data sourced from setlist.fm.</div></footer>
<script>const search=document.getElementById('songSearch');if(search){{const songs=[...document.querySelectorAll('.song')];search.addEventListener('input',()=>{{const q=search.value.trim().toLowerCase();songs.forEach(song=>song.classList.toggle('hidden',!song.dataset.song.includes(q)))}});}}</script>
</body></html>"""


def main() -> int:
    api_key = os.environ.get("SETLIST_FM_API_KEY", "").strip()
    if not api_key:
        print("SETLIST_FM_API_KEY is missing.", file=sys.stderr)
        return 2

    try:
        shows = fetch_shows(api_key)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        print(f"setlist.fm request failed: {exc}", file=sys.stderr)
        return 1

    enrich(shows)
    song_stats = build_song_stats(shows)

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "artist": {"name": "Avenged Sevenfold", "mbid": ARTIST_MBID},
        "tour": {
            "name": "North American Tour 2026",
            "start_date": TOUR_START.isoformat(),
            "countries": sorted(ALLOWED_COUNTRIES),
            "scheduled_shows": SCHEDULED_SHOWS,
        },
        "shows": shows,
        "song_stats": song_stats,
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    INDEX_FILE.write_text(render(payload), encoding="utf-8")

    print(f"Generated index.html using {len(shows)} completed show(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
