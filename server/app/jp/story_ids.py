"""JP puts the FULL story id on the wire, never the short one.

Some shared and scenario producers store `short_story_id` directly, so this
rewrites the reply's events on the way out. Global performs the same
canonicalization at its transport boundary. Across every JP capture (umacap
DYI / Beyond Dreams / Venus / URA and the headless DYI careers), all 1,261
served stories that have a short id went out under their `story_id`; not one
short id was served.

This rewrites the reply's events on the way out, so every producer (the
engine, the hardcoded URA and goal-scene short ids) gets the JP form. State
keeps whatever the pipeline stored; only the wire changes.
"""

from __future__ import annotations

import functools

from .. import master_data


@functools.lru_cache(maxsize=8192)
def full_story_id(story_id: int) -> int:
    """The story_id whose short copy is `story_id`; `story_id` itself when it
    is not a short id (a full id, or a row with no short copy)."""
    if master_data.query_one("SELECT 1 FROM single_mode_story_data WHERE story_id=?",
                             (story_id,)):
        return story_id
    row = master_data.query_one(
        "SELECT story_id FROM single_mode_story_data WHERE short_story_id=? ORDER BY id",
        (story_id,))
    return int(row["story_id"]) if row else story_id


def _fix(events) -> None:
    for ev in events or ():
        if not isinstance(ev, dict):
            continue
        try:
            sid = int(ev.get("story_id") or 0)
        except (TypeError, ValueError):
            continue
        if sid > 0:
            ev["story_id"] = full_story_id(sid)


def apply(resp: dict) -> None:
    """Rewrite every unchecked_event_array in the reply to full story ids."""
    def walk(node):
        if isinstance(node, dict):
            for key, val in node.items():
                if key == "unchecked_event_array" and isinstance(val, list):
                    _fix(val)
                else:
                    walk(val)
        elif isinstance(node, list):
            for val in node:
                walk(val)

    walk(resp.get("data"))
