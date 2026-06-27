"""Preference store: remember what the user decided last time so we don't
re-suggest the same cleanup.

Each entry records a (skill_id, signal, diagnosis_type, hash) combination plus
enough at-decision context to detect later whether the decision is still
relevant. Staleness is computed by `filter_active` per diagnosis_type:

- positioning_unclear / trigger_boundary_overlap → stale when description_hash
  drifts.
- boundary_inflation / boundary_deflation → stale when description_hash drifts
  OR (if both versions are known) the version changes OR the body shifted by
  more than WORD_DELTA_THRESHOLD words / H2_DELTA_THRESHOLD section headings.
  The body thresholds are deliberately coarse: typo fixes and reformatting
  shouldn't invalidate a user's "keep" judgement, but a meaningful capability
  change should.
- positioning_overlap → stale when description_hash drifts OR any recorded
  adversary has vanished from the inventory or had its description change.
  The user's "keep" was conditional on the specific overlap context; if that
  context shifts, re-evaluate.
"""

from __future__ import annotations

import json
from pathlib import Path

from sibyl.config import plugin_data_dir


WORD_DELTA_THRESHOLD = 0.20
H2_DELTA_THRESHOLD = 1


def _path() -> Path:
    return plugin_data_dir() / "preferences.json"


def load() -> dict:
    p = _path()
    if not p.exists():
        return {"version": 1, "preferences": []}
    return json.loads(p.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    _path().write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _key(entry: dict) -> tuple:
    return (
        entry["skill_id"],
        entry["signal"],
        entry.get("diagnosis_type", ""),
        entry.get("description_hash_at_decision", ""),
    )


def append(entries: list[dict]) -> dict:
    """Append new preference entries, deduplicating by the four-element key.

    When a duplicate arrives, bump occurrences and refresh last_seen_run /
    context — these represent the user re-confirming the same call."""
    data = load()
    index = {_key(e): i for i, e in enumerate(data["preferences"])}
    for entry in entries:
        k = _key(entry)
        if k in index:
            prev = data["preferences"][index[k]]
            prev["occurrences"] = prev.get("occurrences", 1) + 1
            prev["last_seen_run"] = entry.get("last_seen_run", prev.get("last_seen_run"))
            if entry.get("context"):
                prev["context"] = entry["context"]
        else:
            data["preferences"].append(entry)
            index[k] = len(data["preferences"]) - 1
    _save(data)
    return data


def _is_stale_simple(pref: dict, state_by_id: dict) -> bool:
    me = state_by_id.get(pref["skill_id"])
    if me is None:
        return True
    return me.get("description_hash") != pref.get("description_hash_at_decision")


def _is_stale_boundary(pref: dict, state_by_id: dict) -> bool:
    me = state_by_id.get(pref["skill_id"])
    if me is None:
        return True
    if me.get("description_hash") != pref.get("description_hash_at_decision"):
        return True
    v_old = pref.get("version_at_decision")
    v_new = me.get("version")
    if v_old and v_new:
        return v_old != v_new
    old_words = pref.get("body_word_count_at_decision", 0) or 0
    new_words = me.get("body_word_count", 0) or 0
    word_delta = abs(new_words - old_words) / max(old_words, 1)
    h2_delta = abs(
        (me.get("body_h2_count") or 0) - (pref.get("body_h2_count_at_decision") or 0)
    )
    return word_delta >= WORD_DELTA_THRESHOLD or h2_delta >= H2_DELTA_THRESHOLD


def _is_stale_overlap(pref: dict, state_by_id: dict) -> bool:
    me = state_by_id.get(pref["skill_id"])
    if me is None:
        return True
    if me.get("description_hash") != pref.get("description_hash_at_decision"):
        return True
    for adv in pref.get("adversaries_at_decision", []):
        cur = state_by_id.get(adv["skill_id"])
        if cur is None:
            return True
        if cur.get("description_hash") != adv.get("description_hash"):
            return True
    return False


_STALE_FN_BY_DIAGNOSIS = {
    "positioning_overlap": _is_stale_overlap,
    "boundary_inflation": _is_stale_boundary,
    "boundary_deflation": _is_stale_boundary,
    "positioning_unclear": _is_stale_simple,
    "trigger_boundary_overlap": _is_stale_simple,
}


def filter_active(prefs: dict, state_by_id: dict) -> dict:
    """Split preferences into active (still applicable) vs stale (re-evaluate).

    state_by_id maps skill_id → {description_hash, version, body_word_count,
    body_h2_count}; pass it the current inventory data merged into a dict.
    """
    out = {"version": prefs.get("version", 1), "active": [], "stale": []}
    for p in prefs.get("preferences", []):
        check = _STALE_FN_BY_DIAGNOSIS.get(p.get("diagnosis_type"), _is_stale_simple)
        bucket = "stale" if check(p, state_by_id) else "active"
        out[bucket].append(p)
    return out
