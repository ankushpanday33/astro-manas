"""Module B: Personality from Birth Panchang (PRD section 4), at the exact birth instant.

Astronomy (ephemeris.py) and interpretation (config tables) stay separate layers.
"""
from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Callable

from . import config as C
from .ephemeris import ayanamsha_lahiri, sun_moon_sidereal, sunrise_utc

SPAN = 13 + 20 / 60

# IANA zones used by the demo. Production derives the zone from lat/long and uses the tz database (with DST).
TZ_OFFSETS_H = {"Asia/Kolkata": 5.5, "Asia/Dubai": 4.0, "Asia/Kathmandu": 5.75, "Europe/London": 0.0,
                "America/New_York": -5.0, "Asia/Singapore": 8.0}


def _indices(dt_utc: datetime) -> dict[str, int]:
    sun, moon = sun_moon_sidereal(dt_utc)
    D = (moon - sun + 360) % 360
    return {"tithi": math.floor(D / 12) + 1, "nakshatra": math.floor(moon / SPAN) + 1,
            "yoga": math.floor(((sun + moon) % 360) / SPAN) + 1, "karana": math.floor(D / 6)}


def _boundaries(dt_utc: datetime, key: str) -> tuple[datetime, datetime]:
    """Start and end of the Anga containing dt (PRD 4.10: store boundaries, not just the name). Precision 1 minute."""
    target = _indices(dt_utc)[key]

    def edge(direction: int) -> datetime:
        inside, step = dt_utc, timedelta(minutes=30 * direction)
        probe = inside + step
        for _ in range(200):
            if _indices(probe)[key] != target:
                break
            inside, probe = probe, probe + step
        lo, hi = inside, probe
        while abs((hi - lo).total_seconds()) > 60:
            mid = lo + (hi - lo) / 2
            if _indices(mid)[key] == target:
                lo = mid
            else:
                hi = mid
        return lo

    return edge(-1), edge(1)


def karana_name(k: int) -> tuple[str, str]:
    if k == 0:
        return "Kimstughna", "FIXED"
    if k <= 56:
        return C.MOVABLE_KARANA[(k - 1) % 7], "MOVABLE"
    return {57: "Shakuni", 58: "Chatushpada"}.get(k, "Naga"), "FIXED"


def tithi_name(idx: int) -> tuple[str, str, str]:
    paksha = "SHUKLA" if idx <= 15 else "KRISHNA"
    if idx == 15:
        base = "Purnima"
    elif idx == 30:
        base = "Amavasya"
    else:
        base = C.TITHI_NAMES[(idx - 1) % 15]
    full = base if base in {"Purnima", "Amavasya"} else f"{'Shukla' if paksha == 'SHUKLA' else 'Krishna'} {base}"
    return full, base, paksha


def compute(dob: date, birth_time: time | None, confidence: str, window_min: int | None,
            lat: float | None, lon: float | None, tz_name: str | None) -> dict[str, Any] | None:
    """Flat columns for groups E, F, G plus panchang_report (PRD 4.9). None when time or place is missing (PRD 5.1)."""
    if birth_time is None or lat is None or lon is None or confidence == "UNKNOWN":
        return None
    offset = timedelta(hours=TZ_OFFSETS_H.get(tz_name or "Asia/Kolkata", 5.5))
    local_naive = datetime.combine(dob, birth_time)
    t = (local_naive - offset).replace(tzinfo=timezone.utc)

    sun, moon = sun_moon_sidereal(t)
    idx = _indices(t)
    tname, tbase, paksha = tithi_name(idx["tithi"])

    rise = sunrise_utc(dob, lat, lon)
    vara_date = dob
    adjusted = bool(rise and t < rise)
    if adjusted:
        vara_date -= timedelta(days=1)
    vname, vhindi, vlord, vtags = C.VARA[vara_date.weekday()]

    n_i = idx["nakshatra"]
    nname, ntags = C.NAKSHATRAS[n_i - 1]
    pada = math.floor((moon % SPAN) / (SPAN / 4)) + 1
    navamsa = C.SIGNS[math.floor(moon * 9 / 30) % 12]
    yname, ytheme = C.YOGAS[idx["yoga"] - 1]
    kname, ktype = karana_name(idx["karana"])

    bounds = {k: _boundaries(t, k) for k in ("tithi", "nakshatra", "yoga", "karana")}

    uncertain: list[str] = []
    if confidence == "APPROXIMATE" and window_min:
        w = timedelta(minutes=window_min)
        before, after = _indices(t - w), _indices(t + w)
        uncertain = [k.upper() for k in idx if before[k] != idx[k] or after[k] != idx[k]]
        if rise and ((t - w < rise) != (t + w < rise)):
            uncertain.append("VARA")

    def score(key: str) -> int:
        s = C.ANGA_SCORE_BASE
        if key != "vara":
            start, end = bounds[key]
            span = (end - start).total_seconds() or 1
            pos = (t - start).total_seconds() / span
            if 0.1 <= pos <= 0.9:
                s += C.ANGA_SCORE_CLEAR
        elif not adjusted:
            s += C.ANGA_SCORE_CLEAR
        if key.upper() in uncertain:
            s += C.ANGA_SCORE_UNCERTAIN
        return max(0, min(100, s))

    sc = {k: score(k) for k in ("nakshatra", "tithi", "yoga", "vara", "karana")}
    overall = round(sum(C.PANCHANG_WEIGHTS[k] * sc[k] for k in C.PANCHANG_WEIGHTS), 2)
    iso = lambda d: d.isoformat(timespec="minutes")

    flat: dict[str, Any] = {
        "birth_datetime_utc": iso(t), "calculation_system": "DRIK_LAHIRI", "ayanamsha": "LAHIRI",
        "ayanamsha_value": round(ayanamsha_lahiri(t), 4),
        "sun_longitude": round(sun, 6), "moon_longitude": round(moon, 6),
        "local_sunrise_utc": iso(rise) if rise else None,
        "tithi_index": idx["tithi"], "tithi_name": tname, "paksha": paksha,
        "tithi_start_utc": iso(bounds["tithi"][0]), "tithi_end_utc": iso(bounds["tithi"][1]),
        "vara_name": vname, "vara_lord": vlord, "vara_sunrise_adjusted": adjusted,
        "nakshatra_index": n_i, "nakshatra_name": nname, "nakshatra_lord": C.VIMSHOTTARI[(n_i - 1) % 9],
        "nakshatra_pada": pada, "navamsa_sign": navamsa,
        "nakshatra_start_utc": iso(bounds["nakshatra"][0]), "nakshatra_end_utc": iso(bounds["nakshatra"][1]),
        "yoga_index": idx["yoga"], "yoga_name": yname,
        "yoga_start_utc": iso(bounds["yoga"][0]), "yoga_end_utc": iso(bounds["yoga"][1]),
        "karana_k": idx["karana"], "karana_name": kname, "karana_type": ktype,
        "karana_start_utc": iso(bounds["karana"][0]), "karana_end_utc": iso(bounds["karana"][1]),
        "tithi_tags": C.TITHI_THEMES[tbase], "vara_tags": vtags, "nakshatra_tags": ntags,
        "yoga_tags": [x.strip() for x in ytheme.split(",")], "karana_tags": C.KARANA_THEMES[kname],
        "panchang_uncertain_angas": uncertain,
        "score_mind_emotions": sc["tithi"], "score_behaviour": sc["vara"], "score_core_personality": sc["nakshatra"],
        "score_thinking_style": sc["yoga"], "score_working_style": sc["karana"],
        "overall_profile_score": overall, "panchang_score_weights": C.PANCHANG_WEIGHTS,
    }
    flat["panchang_report"] = {
        "calculation_system": "DRIK_LAHIRI", "birth_datetime": iso(t),
        "birth_location": {"latitude": lat, "longitude": lon, "timezone": tz_name},
        "panchang": {
            "tithi": {"name": tname, "index": idx["tithi"], "paksha": paksha, "start": flat["tithi_start_utc"],
                      "end": flat["tithi_end_utc"], "personality_tags": flat["tithi_tags"]},
            "vara": {"name": vname, "lord": vlord, "personality_tags": vtags},
            "nakshatra": {"name": nname, "lord": flat["nakshatra_lord"], "pada": pada, "navamsa_sign": navamsa,
                          "personality_tags": ntags},
            "yoga": {"name": yname, "index": idx["yoga"], "personality_tags": flat["yoga_tags"]},
            "karana": {"name": kname, "type": ktype, "personality_tags": flat["karana_tags"]},
        },
        "personality_dimensions": {"mind_emotions": sc["tithi"], "core_personality": sc["nakshatra"], "behaviour": sc["vara"],
                                   "thinking_style": sc["yoga"], "working_style": sc["karana"], "overall_profile_score": overall},
        "birth_time_confidence": confidence, "rule_version": C.RULE_VERSION,
        "ephemeris_note": "Demo ephemeris (Meeus main terms, linear Lahiri). Swap for a validated ephemeris before production.",
    }
    return flat
