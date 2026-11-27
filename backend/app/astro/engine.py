"""Compute pipeline (PRD 5.5): inputs -> Module A + Module B -> one transactional write to the "user" table -> AI narrative.

The app and the decision brain read stored columns only; nothing is recomputed on read.
"""
from __future__ import annotations

import json
from datetime import date, datetime, time
from typing import Any

from .. import llm, store
from . import config as C
from . import numerology, panchang

# Column groups A to I from PRD 5.2 (SQLite stores arrays and JSON as JSON text).
USER_COLUMNS = [
    # A
    "id", "full_name", "numerology_name", "name_correction_trials", "dob", "birth_time", "birth_time_confidence",
    "birth_time_window_min", "birth_place_name", "birth_latitude", "birth_longitude", "birth_timezone", "birth_datetime_utc",
    # B
    "radical_number", "radical_compound", "radical_planet", "radical_calculation", "destiny_number", "destiny_compound",
    "destiny_planet", "destiny_calculation", "name_number", "name_compound", "name_planet", "name_calculation",
    # C
    "number_scores", "lucky_numbers", "neutral_numbers", "challenging_numbers", "common_challenging_numbers",
    "lucky_colours_primary", "lucky_colours_secondary", "lucky_metals", "traditional_gemstones", "gemstone_prescription",
    # D
    "loshu_variant", "loshu_grid", "loshu_missing_digits", "loshu_complete_planes",
    # E
    "calculation_system", "ayanamsha", "sun_longitude", "moon_longitude", "local_sunrise_utc",
    # F
    "tithi_index", "tithi_name", "paksha", "tithi_start_utc", "tithi_end_utc", "vara_name", "vara_lord",
    "vara_sunrise_adjusted", "nakshatra_index", "nakshatra_name", "nakshatra_lord", "nakshatra_pada", "navamsa_sign",
    "nakshatra_start_utc", "nakshatra_end_utc", "yoga_index", "yoga_name", "yoga_start_utc", "yoga_end_utc",
    "karana_k", "karana_name", "karana_type", "karana_start_utc", "karana_end_utc",
    "tithi_tags", "vara_tags", "nakshatra_tags", "yoga_tags", "karana_tags", "panchang_uncertain_angas",
    # G
    "score_mind_emotions", "score_behaviour", "score_core_personality", "score_thinking_style", "score_working_style",
    "overall_profile_score", "panchang_score_weights",
    # H
    "personality_title", "core_traits", "strengths", "development_areas", "career_work_style", "relationship_style",
    "interpretation_sources", "ai_model", "ai_report_generated_at",
    # I
    "numerology_report", "panchang_report", "dob_method", "name_method", "compatibility_version", "rule_version",
    "source_tradition", "numerology_computed_at", "panchang_computed_at", "astro_consent_at", "created_at", "updated_at",
]
# Groups are cut at their first column (PRD 5.2), so adding a column can never shift a neighbour into the wrong group.
_GROUP_START = {"A": "id", "B": "radical_number", "C": "number_scores", "D": "loshu_variant", "E": "calculation_system",
                "F": "tithi_index", "G": "score_mind_emotions", "H": "personality_title", "I": "numerology_report"}
_starts = [(g, USER_COLUMNS.index(c)) for g, c in _GROUP_START.items()]
GROUPS = {g: USER_COLUMNS[i:(_starts[k + 1][1] if k + 1 < len(_starts) else len(USER_COLUMNS))] for k, (g, i) in enumerate(_starts)}

DDL = 'CREATE TABLE IF NOT EXISTS "user" (' + ", ".join(
    f'"{c}" TEXT PRIMARY KEY' if c == "id" else f'"{c}"' for c in USER_COLUMNS) + ")"


def _enc(v: Any) -> Any:
    return json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict, bool)) else v


def _dec(v: Any) -> Any:
    if isinstance(v, str) and v[:1] in "[{" or v in ("true", "false"):
        try:
            return json.loads(v)
        except (TypeError, json.JSONDecodeError):
            return v
    return v


def init() -> None:
    with store.db() as conn:
        conn.execute(DDL)
        for col in ("radical_number", "destiny_number", "nakshatra_index", "vara_lord", "rule_version"):
            conn.execute(f'CREATE INDEX IF NOT EXISTS idx_user_{col} ON "user"("{col}")')


def reset() -> None:
    with store.db() as conn:
        conn.execute('DELETE FROM "user"')


def get_user_row(user_id: str) -> dict[str, Any] | None:
    with store.db() as conn:
        row = conn.execute('SELECT * FROM "user" WHERE id=?', (user_id,)).fetchone()
    return {k: _dec(row[k]) for k in row.keys()} if row else None


def _narrative(row: dict[str, Any]) -> dict[str, Any]:
    """Group H. Rules write it from stored tags; Claude rewrites it when enabled, from the stored JSON only."""
    has_p = row.get("nakshatra_name") is not None
    tags = (row.get("nakshatra_tags") or []) + (row.get("yoga_tags") or [])
    title_bits = tags[:2] if has_p else [row["radical_planet"].title(), row["destiny_planet"].title()]
    out = {
        "personality_title": f"The {' and '.join(title_bits)} {'Soul' if has_p else 'Path'}",
        "core_traits": ([f"Core nature from {row['nakshatra_name']} Nakshatra: {', '.join(row['nakshatra_tags'])}.",
                         f"Mind shaped by {row['tithi_name']}: {', '.join(row['tithi_tags'])}."] if has_p else
                        [f"Radical {row['radical_number']} ({row['radical_planet'].title()}) and Destiny {row['destiny_number']} ({row['destiny_planet'].title()})."]),
        "strengths": (row.get("nakshatra_tags", []) + row.get("yoga_tags", []) + row.get("karana_tags", []))[:4] if has_p else [],
        "development_areas": ["Balance intensity with rest", "Pause before quick decisions"] if has_p else [],
        "career_work_style": f"{row['karana_name']} Karana and {row['yoga_name']} Yoga: {', '.join(row['karana_tags'] + row['yoga_tags'])}." if has_p else None,
        "relationship_style": f"{row['vara_name']} birth ({row['vara_lord'].title()}) with {row['nakshatra_name']}: {', '.join(row['vara_tags'][:2])}." if has_p else None,
        "interpretation_sources": [f"PRD tables {C.SOURCE_TRADITION} v{C.RULE_VERSION}"],
        "ai_model": "rules-v1",
    }
    if llm.enabled():
        report = {"numerology": row.get("numerology_report"), "panchang": row.get("panchang_report")}
        res = llm.ask_json(
            "You write a short personality report from a Vedic astrology engine's stored output. Use only the values given; "
            "never invent a Panchang element, planet or number. Present it as traditional guidance, not a proven outcome. "
            "Never prescribe gemstones. Constructive tone.",
            json.dumps(report, ensure_ascii=False),
            {"type": "object", "properties": {
                "personality_title": {"type": "string"}, "core_traits": {"type": "array", "items": {"type": "string"}},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "development_areas": {"type": "array", "items": {"type": "string"}},
                "career_work_style": {"type": "string"}, "relationship_style": {"type": "string"}}},
            max_tokens=1500)
        if res:
            out.update(res)
            out["ai_model"] = llm.MODEL
    out["ai_report_generated_at"] = datetime.now().isoformat(timespec="seconds")
    return out


def compute_and_store(profile: dict[str, Any]) -> dict[str, Any] | None:
    """profile: one customers row. Returns the stored user row, or None without astro consent (PRD 5.8)."""
    if not profile.get("astro_consent_at"):
        return None
    now = datetime.now().isoformat(timespec="seconds")
    dob = date.fromisoformat(profile["dob"])
    from ..ingest import parse_time

    hhmm = parse_time(profile.get("birth_time"))
    bt = time.fromisoformat(hhmm) if hhmm else None
    lat = float(profile["birth_latitude"]) if profile.get("birth_latitude") not in (None, "") else None
    lon = float(profile["birth_longitude"]) if profile.get("birth_longitude") not in (None, "") else None
    window = int(profile["birth_time_window_min"]) if profile.get("birth_time_window_min") not in (None, "") else None
    conf = profile.get("birth_time_confidence") or ("EXACT" if bt else "UNKNOWN")

    row: dict[str, Any] = {c: None for c in USER_COLUMNS}
    row.update({
        "id": profile["customer_id"], "full_name": profile.get("name"), "numerology_name": profile.get("numerology_name") or profile.get("name", "").split()[0].upper(),
        "name_correction_trials": [], "dob": dob.isoformat(), "birth_time": bt.isoformat(timespec="minutes") if bt else None,
        "birth_time_confidence": conf, "birth_time_window_min": window, "birth_place_name": profile.get("birth_place_name"),
        "birth_latitude": lat, "birth_longitude": lon, "birth_timezone": profile.get("birth_timezone") or "Asia/Kolkata",
        "rule_version": C.RULE_VERSION, "source_tradition": C.SOURCE_TRADITION, "astro_consent_at": profile["astro_consent_at"],
        "created_at": now, "updated_at": now,
    })
    row.update(numerology.compute(dob, row["numerology_name"]))
    row["numerology_computed_at"] = now
    p = panchang.compute(dob, bt, conf, window, lat, lon, row["birth_timezone"])
    if p:
        row.update({k: v for k, v in p.items() if k in row})
        row["panchang_computed_at"] = now
    row.update(_narrative(row))

    # One transaction: never leave half-updated groups (PRD rule 8).
    cols = ", ".join(f'"{c}"' for c in USER_COLUMNS)
    with store.db() as conn:
        conn.execute(f'INSERT OR REPLACE INTO "user" ({cols}) VALUES ({", ".join("?" * len(USER_COLUMNS))})',
                     [_enc(row[c]) for c in USER_COLUMNS])
    return row


def add_name_trial(user_id: str, spelling: str) -> dict[str, Any]:
    """Name Correction: append only, never overwrite the main result (PRD 3.5)."""
    row = get_user_row(user_id)
    if not row:
        raise KeyError(user_id)
    trial = numerology.name_trial(spelling)
    trials = (row.get("name_correction_trials") or []) + [trial]
    with store.db() as conn:
        conn.execute('UPDATE "user" SET name_correction_trials=?, updated_at=? WHERE id=?',
                     (json.dumps(trials), datetime.now().isoformat(timespec="seconds"), user_id))
    return {"trial": trial, "main": {"name": row["numerology_name"], "value": row["name_number"], "compound": row["name_compound"]}}
