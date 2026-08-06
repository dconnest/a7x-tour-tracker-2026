from __future__ import annotations

import datetime as dt
import html
from typing import Any

from .config import SCHEDULED_SHOWS, TOUR_SCHEDULE
from .stats import song_names


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def location(show: dict[str, Any]) -> str:
    region = show.get("state") or show.get("country")
    return f'{show["city"]}, {region}' if region else show["city"]


def next_scheduled_show(shows: list[dict[str, Any]]) -> dict[str, str] | None:
    completed_dates = {show["date"] for show in shows}

    for scheduled in TOUR_SCHEDULE:
        if scheduled["date"] not in completed_dates:
            return scheduled

    return None


def render_site(data: dict[str, Any]) -> str:
    shows = data["shows"]
    stats = data["song_stats"]
    latest = shows[-1] if shows else None
    unique_songs = len(stats)
    progress = min(100, round(100 * len(shows) / SCHEDULED_SHOWS, 1))
    average_length = (
        round(sum(show["set_length"] for show in shows) / len(shows), 1)
        if shows
        else 0
    )

    show_cards = ""
    for show in reversed(shows):
        if show["number"] == 1:
            changes = "Opening-night tour rotation established."
        elif show["added"] or show["dropped"]:
            pieces = []
            if show["added"]:
                pieces.append("Added: " + ", ".join(show["added"]))
            if show["dropped"]:
                pieces.append("Dropped: " + ", ".join(show["dropped"]))
            changes = " · ".join(pieces)
        else:
            changes = "No song changes from the previous tracked show."

        show_cards += f"""
        <article class="showCard">
          <span class="muted">Show #{show["number"]} · {esc(show["display_date"])}</span>
          <h3>{esc(show["venue"])}</h3>
          <p>{esc(location(show))}</p>
          <div class="highlight">{esc(changes)}</div>
          <a class="source" href="{esc(show["url"])}" target="_blank" rel="noopener">
            Source: setlist.fm ↗
          </a>
        </article>"""

    latest_setlist = ""
    if latest:
        for position, song in enumerate(latest["songs"], start=1):
            labels: list[str] = []
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
                <div class="note">
                  {esc(" · ".join(labels) or f'Appearance at Show #{latest["number"]}')}
                </div>
              </div>
            </div>"""

    song_rows = "".join(
        f"""<div class="songRow"><strong>{esc(song["name"])}</strong>
        <span>{song["appearances"]}</span><span>{song["rate"]}%</span>
        <span>{song["streak"]}</span><span>{song["average_position"]}</span></div>"""
        for song in stats
    )

    heat_headers = "".join(
        f'<div class="heatHead">#{show["number"]}</div>' for show in shows
    )
    heat_rows = ""
    for song in stats:
        cells = "".join(
            '<div class="heatCell played">✓</div>'
            if song["name"] in song_names(show)
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
          <div class="eventDate">
            {esc(dt.date.fromisoformat(show["date"]).strftime("%b %d").upper())}
          </div>
          <div class="eventBody">
            <strong>{esc(show["venue"])} · {esc(location(show))}</strong>
            <span class="muted">{esc(narrative)}</span>
          </div>
        </div>"""

    if latest:
        added = ", ".join(latest["added"]) or "None"
        dropped = ", ".join(latest["dropped"]) or "None"
        returned = ", ".join(latest["returned"]) or "None"
        similarity = (
            f'{latest["similarity"]}%'
            if latest["similarity"] is not None
            else "Opening show"
        )
        latest_title = latest["venue"]
        latest_meta = f'{location(latest)} · {latest["display_date"]}'
    else:
        added = dropped = returned = "None"
        similarity = "—"
        latest_title = "Waiting for the first confirmed show"
        latest_meta = "The automatic updater is connected."

    updated_at = data.get("generated_at", "")
    try:
        parsed = dt.datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        updated_display = parsed.strftime("%B %d, %Y · %H:%M UTC").replace(" 0", " ")
    except Exception:
        updated_display = "Not yet available"

    heat_columns = max(1, len(shows))

    next_show = next_scheduled_show(shows)

    if next_show:
        next_date = dt.date.fromisoformat(next_show["date"])
        next_date_display = next_date.strftime("%A, %B %d, %Y").replace(" 0", " ")
        next_show_html = f"""
        <section class="shell section">
          <article class="panel nextShow">
            <div>
              <p class="eyebrow">Next scheduled show</p>
              <h2>{esc(next_show["venue"])}</h2>
              <p class="muted">
                {esc(next_show["city"])}, {esc(next_show["region"])}
                · {esc(next_date_display)}
              </p>
            </div>
            <div class="nextShowDate">
              <strong>{esc(next_date.strftime("%b %d").upper())}</strong>
              <span>{esc(next_date.strftime("%Y"))}</span>
            </div>
          </article>
        </section>
        """
    else:
        next_show_html = """
        <section class="shell section">
          <article class="panel nextShow">
            <div>
              <p class="eyebrow">Next scheduled show</p>
              <h2>Tour complete</h2>
              <p class="muted">All scheduled North American dates are complete.</p>
            </div>
          </article>
        </section>
        """

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
.nextShow{{display:flex;align-items:center;justify-content:space-between;gap:24px;border-left:4px solid var(--red)}}
.nextShow h2{{margin:6px 0 8px;font-size:32px}}
.nextShowDate{{min-width:120px;text-align:center;padding:16px;border-radius:14px;background:rgba(223,37,45,.10);border:1px solid rgba(223,37,45,.25)}}
.nextShowDate strong,.nextShowDate span{{display:block}}
.nextShowDate strong{{font-size:24px;color:var(--red2)}}
.nextShowDate span{{margin-top:3px;color:var(--muted)}}
.showCard h3{{font-size:22px;margin:10px 0 6px}}.showCard p{{margin:0;color:var(--muted)}}.miniCard{{padding:18px;text-align:center;border:1px solid var(--line);border-radius:16px;background:var(--panel2)}}.miniCard strong{{display:block;font-size:30px;margin-top:6px;overflow-wrap:anywhere}}.search{{width:100%;max-width:280px;padding:11px 13px;border-radius:12px;border:1px solid var(--line);background:#0d0f14;color:#fff}}
.setlist{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}.song{{display:flex;gap:13px;padding:14px 15px;background:var(--panel);border:1px solid var(--line);border-radius:14px}}.songNum{{width:28px;height:28px;display:grid;place-items:center;border-radius:50%;background:rgba(223,37,45,.14);color:#ff8b90;font-size:12px;font-weight:900;flex:none}}.songTitle{{font-weight:800}}.note{{font-size:12px;color:var(--muted);margin-top:4px}}
.songTable{{border:1px solid var(--line);border-radius:18px;overflow:hidden}}.songTableHead,.songRow{{display:grid;grid-template-columns:2fr repeat(4,1fr);gap:12px;padding:16px 20px}}.songTableHead{{background:#20232c;color:var(--muted);font-size:12px;text-transform:uppercase}}.songRow{{background:var(--panel);border-top:1px solid var(--line)}}.heatWrap{{overflow-x:auto}}.heatmap{{min-width:max(760px,calc(220px + {heat_columns} * 72px));display:grid;grid-template-columns:220px repeat({heat_columns},64px);gap:8px;align-items:center}}.heatHead{{font-size:12px;color:var(--muted);text-align:center}}.heatRow{{display:contents}}.heatCell{{height:38px;border-radius:8px;background:#222630;display:grid;place-items:center}}.heatCell.played{{background:var(--red)}}.timeline{{display:grid;gap:14px}}.event{{display:grid;grid-template-columns:100px 1fr;gap:18px}}.eventDate{{font-weight:900;color:var(--red2)}}.eventBody{{border-left:2px solid var(--line);padding:0 0 20px 18px}}footer{{border-top:1px solid var(--line);padding:30px 0 42px;color:var(--muted);font-size:13px}}.hidden{{display:none!important}}
@media(max-width:900px){{nav{{display:none}}.statsGrid,.compareGrid{{grid-template-columns:repeat(2,1fr)}}.featureGrid,.showGrid{{grid-template-columns:1fr}}}}@media(max-width:620px){{.nextShow{{align-items:flex-start;flex-direction:column}}.statsGrid,.compareGrid,.setlist{{grid-template-columns:1fr}}.songTableHead{{display:none}}.songRow{{grid-template-columns:1fr 60px 60px}}.songRow span:nth-child(4),.songRow span:nth-child(5){{display:none}}.event{{grid-template-columns:1fr}}.eventBody{{border-left:0;border-top:1px solid var(--line);padding:12px 0 18px}}}}
</style>
</head>
<body>
<header><div class="shell nav"><a class="brand" href="#top"><span class="brandMark">A7X</span><span>Tour Tracker <b>2026</b></span></a><nav><a href="#dashboard">Dashboard</a><a href="#shows">Shows</a><a href="#songs">Songs</a><a href="#heatmap">Heat Map</a><a href="#history">History</a></nav></div></header>
<main id="top">
<section class="hero"><div class="shell"><p class="eyebrow">North American Tour 2026</p><h1>Every show.<br>Every song.<br><em>Every change.</em></h1><p class="lede">Automatically updated from confirmed setlist.fm data.</p></div></section>
<section class="shell section" id="dashboard">
<div class="statsGrid grid"><article class="statCard"><span>Shows completed</span><strong>{len(shows)} / {SCHEDULED_SHOWS}</strong><small>{progress}% of scheduled dates</small></article><article class="statCard"><span>Unique songs</span><strong>{unique_songs}</strong><small>Across tracked shows</small></article><article class="statCard"><span>Average set length</span><strong>{average_length}</strong><small>Performed songs</small></article><article class="statCard"><span>Latest similarity</span><strong>{similarity}</strong><small>Compared with prior show</small></article></div>
<div class="featureGrid grid"><article class="panel feature"><p class="eyebrow">Latest completed show</p><h2>{esc(latest_title)}</h2><p class="muted">{esc(latest_meta)}</p><div class="highlight"><strong>Latest changes:</strong> Added: {esc(added)} · Dropped: {esc(dropped)} · Returned: {esc(returned)}</div></article><article class="panel"><p class="eyebrow">Tracker status</p><div class="progress"><span></span></div><h3>{len(shows)} of {SCHEDULED_SHOWS} shows complete</h3><p class="muted">Last generated: {esc(updated_display)}</p></article></div>
</section>
{next_show_html}
<section class="shell section" id="shows"><div class="sectionHead"><div><p class="eyebrow">Tracked shows</p><h2>Completed performances</h2></div></div><div class="showGrid grid">{show_cards or '<div class="panel">No completed setlists have been returned yet.</div>'}</div></section>
<section class="shell section"><div class="sectionHead"><div><p class="eyebrow">Latest comparison</p><h2>What changed?</h2></div></div><div class="compareGrid grid"><div class="miniCard"><span class="muted">Added</span><strong>{esc(added)}</strong></div><div class="miniCard"><span class="muted">Dropped</span><strong>{esc(dropped)}</strong></div><div class="miniCard"><span class="muted">Returned</span><strong>{esc(returned)}</strong></div><div class="miniCard"><span class="muted">Similarity</span><strong>{similarity}</strong></div></div></section>
<section class="shell section"><div class="sectionHead"><div><p class="eyebrow">Latest setlist</p><h2>Running order</h2></div><input id="songSearch" class="search" placeholder="Search songs..."></div><div class="setlist">{latest_setlist or '<div class="panel">Waiting for setlist data.</div>'}</div></section>
<section class="shell section" id="songs"><div class="sectionHead"><div><p class="eyebrow">Song database</p><h2>Current rotation</h2></div></div><div class="songTable"><div class="songTableHead"><span>Song</span><span>Shows</span><span>Rate</span><span>Streak</span><span>Avg. position</span></div>{song_rows}</div></section>
<section class="shell section" id="heatmap"><div class="sectionHead"><div><p class="eyebrow">Heat map</p><h2>Song usage by show</h2></div></div><div class="panel heatWrap"><div class="heatmap"><div></div>{heat_headers}{heat_rows}</div></div></section>
<section class="shell section" id="history"><div class="sectionHead"><div><p class="eyebrow">Tour history</p><h2>The story so far</h2></div></div><div class="panel timeline">{history or '<span class="muted">Waiting for the first completed show.</span>'}</div></section>
</main>
<footer><div class="shell">Unofficial fan project. Not affiliated with Avenged Sevenfold. Data sourced from setlist.fm.</div></footer>
<script>const search=document.getElementById('songSearch');if(search){{const songs=[...document.querySelectorAll('.song')];search.addEventListener('input',()=>{{const q=search.value.trim().toLowerCase();songs.forEach(song=>song.classList.toggle('hidden',!song.dataset.song.includes(q)))}});}}</script>
</body></html>"""
