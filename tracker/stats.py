from __future__ import annotations

from typing import Any


def song_names(show: dict[str, Any]) -> list[str]:
    return [entry["name"] for entry in show["songs"]]


def jaccard_similarity(left_names: list[str], right_names: list[str]) -> int:
    left, right = set(left_names), set(right_names)
    union = left | right
    return round(100 * len(left & right) / len(union)) if union else 100


def enrich_shows(shows: list[dict[str, Any]]) -> None:
    previously_seen: set[str] = set()

    for index, show in enumerate(shows):
        current = song_names(show)
        previous = song_names(shows[index - 1]) if index else []

        show["opener"] = current[0] if current else ""
        show["closer"] = current[-1] if current else ""
        show["set_length"] = len(current)
        show["tour_debuts"] = [song for song in current if song not in previously_seen]
        show["live_debuts"] = [
            entry["name"]
            for entry in show["songs"]
            if "live debut" in entry.get("info", "").casefold()
        ]

        if index:
            show["added"] = [song for song in current if song not in previous]
            show["dropped"] = [song for song in previous if song not in current]
            show["returned"] = [
                song
                for song in show["added"]
                if any(song in song_names(old_show) for old_show in shows[: index - 1])
            ]
            show["similarity"] = jaccard_similarity(current, previous)
        else:
            show["added"] = []
            show["dropped"] = []
            show["returned"] = []
            show["similarity"] = None

        previously_seen.update(current)


def build_song_stats(shows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered_names: list[str] = []
    for show in shows:
        for name in song_names(show):
            if name not in ordered_names:
                ordered_names.append(name)

    total_shows = len(shows)
    stats: list[dict[str, Any]] = []

    for name in ordered_names:
        appearances: list[int] = []
        positions: list[int] = []
        opener_count = 0
        closer_count = 0

        for show in shows:
            names = song_names(show)
            if name in names:
                appearances.append(show["number"])
                positions.append(names.index(name) + 1)
                opener_count += int(names[0] == name)
                closer_count += int(names[-1] == name)

        streak = 0
        for show in reversed(shows):
            if name in song_names(show):
                streak += 1
            else:
                break

        stats.append(
            {
                "name": name,
                "appearances": len(appearances),
                "rate": round(100 * len(appearances) / total_shows) if total_shows else 0,
                "streak": streak,
                "first_show": min(appearances),
                "last_show": max(appearances),
                "average_position": round(sum(positions) / len(positions), 1),
                "opener_count": opener_count,
                "closer_count": closer_count,
            }
        )

    return sorted(stats, key=lambda item: (-item["appearances"], item["name"].casefold()))
