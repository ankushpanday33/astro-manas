"""Episodic memory: what the user said in chats and replies, read in time.

Signals: the life topic on their mind, anxiety, an upcoming event with its resolved date ("interview next week"
written on 02/10 means 09/10), a stated time preference, and opt-outs. English, Hindi (romanised) and Hinglish.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from .. import llm, privacy

KINDS = ["topic", "anxiety", "upcoming_event", "time_preference", "contact_objection"]

TOPICS = {
    "career": r"job|naukri|career|interview|promotion|office|business",
    "marriage": r"shaadi|marriage|rishta|kundli matching|wedding|partner",
    "health": r"health|sehat|bimar|hospital",
    "finance": r"money|paisa|loan|finance|investment",
    "education": r"exam|study|padhai|admission|result",
}
ANXIETY = re.compile(r"tension|worried|worry|pareshan|anxious|dar lag|stress", re.I)
OBJECTION = re.compile(r"notifications? band|stop (?:sending|messag)|mat bhejo|unsubscribe|don'?t message", re.I)
EVENT = re.compile(r"interview|exam|meeting|result|ceremony|engagement", re.I)
TIME_PREF = re.compile(r"(morning|subah)|(evening|shaam|night|raat)", re.I)


def resolve_date(text: str, written: date) -> date | None:
    t = text.lower()
    if re.search(r"day after tomorrow|parso", t):
        return written + timedelta(days=2)
    if re.search(r"tomorrow|\bkal\b", t):
        return written + timedelta(days=1)
    if re.search(r"next week|agle hafte", t):
        return written + timedelta(days=7)
    if re.search(r"next month|agle mahine", t):
        return (written.replace(day=1) + timedelta(days=32)).replace(day=1)
    return None


def _rule_signals(text: str, written: date, ref: dict[str, str]) -> list[dict[str, Any]]:
    base = {"written_on": written.isoformat(), "ref": ref, "method": "rules", "resolved_date": None, "detail": None}
    out = []
    for topic, pat in TOPICS.items():
        if re.search(pat, text, re.I):
            out.append({**base, "kind": "topic", "detail": topic})
    if ANXIETY.search(text):
        out.append({**base, "kind": "anxiety"})
    if OBJECTION.search(text):
        out.append({**base, "kind": "contact_objection"})
    if EVENT.search(text):
        d = resolve_date(text, written)
        out.append({**base, "kind": "upcoming_event", "detail": EVENT.search(text).group(0).lower(),
                    "resolved_date": d.isoformat() if d else None})
    m = TIME_PREF.search(text)
    if m:
        out.append({**base, "kind": "time_preference", "detail": "morning" if m.group(1) else "evening"})
    return out


_LLM_SCHEMA = {"type": "object", "properties": {"signals": {"type": "array", "items": {"type": "object", "properties": {
    "text_index": {"type": "integer"}, "kind": {"type": "string", "enum": KINDS},
    "resolved_date": {"type": ["string", "null"]}, "detail": {"type": ["string", "null"]}}}}}}


def read_texts(texts: list[dict[str, Any]], names: list[str]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for t in texts:
        signals.extend(_rule_signals(t["text"], t["written_on"], t["ref"]))
    if llm.enabled() and texts:
        listing = "\n".join(f"[{i}] written {t['written_on'].isoformat()}: {privacy.scrub_text(t['text'], names)}" for i, t in enumerate(texts))
        res = llm.ask_json(
            "You read short messages users sent to an Indian astrology app (English, Hindi, Hinglish). Extract only explicit "
            "signals. Topic detail must be one of career, marriage, health, finance, education. Resolve relative dates "
            "against the date each text was written.", f"Texts:\n{listing}", _LLM_SCHEMA, max_tokens=1500)
        if res:
            seen = {(s["kind"], s["ref"]["row_id"]) for s in signals}
            for s in res.get("signals", []):
                i = s.get("text_index")
                if isinstance(i, int) and 0 <= i < len(texts) and (s["kind"], texts[i]["ref"]["row_id"]) not in seen:
                    signals.append({"kind": s["kind"], "detail": s.get("detail"), "resolved_date": s.get("resolved_date"),
                                    "written_on": texts[i]["written_on"].isoformat(), "ref": texts[i]["ref"], "method": "llm"})
    signals.sort(key=lambda s: s["written_on"])
    for i, s in enumerate(signals):
        s["id"] = f"mem_{i + 1}"
    return signals
