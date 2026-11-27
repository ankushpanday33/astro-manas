"""Beliefs: judgements formed from facts, each citing the facts it rests on.

Confidence here means sample adequacy (how much evidence there is), never a claim the data cannot back.
With too little evidence a belief returns insufficient_evidence instead of guessing.
When Claude is enabled, an independent judge re-reads every belief against its cited facts;
a disagreement sends the belief to human review instead of acting on it.
"""
from __future__ import annotations

from typing import Any

from .. import llm


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _level(score: float) -> str:
    return "high" if score >= 0.66 else "medium" if score >= 0.4 else "low"


def _belief(bid: str, score: float | None, n: int, need: int, cites: list[str], reasoning: str) -> dict[str, Any]:
    if score is None or n < need:
        return {"id": bid, "value": None, "score": None, "confidence": round(min(1.0, n / max(need * 3, 1)), 2),
                "status": "insufficient_evidence", "cites": cites, "evidence_n": n,
                "reasoning": f"Only {n} observations; at least {need} needed before forming this belief.", "judge": None}
    return {"id": bid, "value": _level(score), "score": round(_clamp(score), 2),
            "confidence": round(min(1.0, n / (need * 3)), 2), "status": "formed", "cites": cites,
            "evidence_n": n, "reasoning": reasoning, "judge": None}


def _num(facts: dict[str, Any], key: str, default: float | None = None) -> float | None:
    v = facts.get(key)
    return default if v is None or isinstance(v, (str, bool)) else float(v)


def _reach(fv: dict[str, Any], channels: list[str], stats: dict[str, Any]) -> dict[str, Any]:
    rates = [r for ch in channels for r in [_num(fv, f"{ch}_read_rate"), _num(fv, f"{ch}_answer_rate")] if r is not None]
    sends = sum(c["sends"] for ws in stats.values() for c in ws.values())
    last_reply = _num(fv, "days_since_last_reply")
    recency = 1.0 if last_reply is not None and last_reply <= 30 else 0.5 if last_reply is not None and last_reply <= 90 else 0.0
    score = 0.7 * max(rates, default=0.0) + 0.3 * recency if rates else None
    best = fv.get("best_responding_slot")
    return _belief("reachability", score, sends, 4,
                   [f"{ch}_read_rate" for ch in channels] + ["days_since_last_reply", "best_responding_slot"],
                   f"Best read/answer rate {max(rates, default=0):.0%}; last reply {int(last_reply) if last_reply is not None else 'never'} days ago; responds best on {best or 'no clear slot'}.")


def astro_beliefs(fv: dict[str, Any], stats: dict[str, Any], pack: dict[str, Any]) -> list[dict[str, Any]]:
    s7 = _num(fv, "sessions_7d", 0) or 0
    deep = _num(fv, "deep_sessions_30d", 0) or 0
    idle = _num(fv, "days_since_last_session")
    trend = _num(fv, "usage_trend")
    n_use = int(s7 + deep)
    eng = min(s7 / 7, 1) * 0.5 + min(deep / 12, 1) * 0.35 + (max(min(trend, 0.5), -0.5) * 0.3 if trend is not None else 0) \
        - (0.3 if idle is not None and idle > 14 else 0) + 0.15
    beliefs = [_belief("engagement", eng, n_use + (1 if idle is not None else 0), 2,
                       ["sessions_7d", "deep_sessions_30d", "usage_trend", "days_since_last_session"],
                       f"{int(s7)} opens this week, {int(deep)} deep sessions in 30 days, trend "
                       f"{'n/a' if trend is None else f'{trend:+.0%}'}, last open {int(idle) if idle is not None else '?'} days ago.")]

    p90 = _num(fv, "purchases_90d", 0) or 0
    chats = _num(fv, "chats_60d", 0) or 0
    intent = 0.15 + min(p90 * 0.18, 0.45) + min(chats * 0.08, 0.24) + (0.1 if fv.get("upcoming_event") else 0)
    beliefs.append(_belief("purchase_intent", intent, int(p90 + chats + deep), 2,
                           ["purchases_90d", "spend_90d", "chats_60d", "upcoming_event", "favourite_product"],
                           f"{int(p90)} purchases (₹{int(_num(fv, 'spend_90d', 0) or 0)}) in 90 days, {int(chats)} astrologer chats"
                           f"{', something important coming up: ' + str(fv['upcoming_event']) if fv.get('upcoming_event') else ''}."))

    topic = fv.get("main_topic")
    t = _belief("topic_focus", 0.8 if topic else None, int(chats) + (1 if topic else 0), 1, ["main_topic", "top_content"],
                f"Their chats keep returning to {topic}." if topic else "No life topic stated yet.")
    if t["status"] == "formed":
        t["value"] = topic
    beliefs.append(t)

    anx = 0.75 if fv.get("anxiety_flag") else 0.15
    beliefs.append(_belief("anxiety", anx, int(chats) + 1, 1, ["anxiety_flag", "main_topic"],
                           "Recent chats sound worried: lead with calm guidance, never with fear or urgency." if fv.get("anxiety_flag")
                           else "No sign of worry in what they wrote."))
    beliefs.append(_reach(fv, pack["channels"], stats))

    pp = fv.get("purchase_propensity_7d")
    beliefs.append(_belief("purchase_propensity", pp, int(_num(fv, "events_30d", 0) or 0), 6,
                           ["purchase_propensity_7d", "cta_clicks_7d", "abandoned_checkout", "top_cta", "competitor_astro_user"],
                           f"Event model gives {pp:.0%} chance of a purchase in 7 days"
                           f"{'; left ' + str(fv['abandoned_checkout']) + ' halfway' if fv.get('abandoned_checkout') else ''}." if pp is not None else ""))
    if fv.get("app_signal_consent"):
        mp = 0.8 if fv.get("money_pressure_flag") else 0.15
        b = _belief("money_pressure", mp, 1, 1, ["money_pressure_flag", "gaming_exposure_flag"],
                    "Protect only: an instant-loan app is installed, so no paid offers and calm copy." if fv.get("money_pressure_flag")
                    else "No instant-loan app among tracked apps.")
        b["protect_only"] = True
        beliefs.append(b)
    return beliefs


BELIEF_BUILDERS = {"astro_engagement": astro_beliefs}

_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {"type": "array", "items": {"type": "object", "properties": {
            "belief_id": {"type": "string"},
            "agrees": {"type": "boolean"},
            "note": {"type": "string", "description": "One sentence: why the cited facts do or do not support the belief."},
        }}}
    },
}


def judge(beliefs: list[dict[str, Any]], facts_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Independent judge: a second pass that checks each formed belief only against the facts it cites."""
    formed = [b for b in beliefs if b["status"] == "formed"]
    if not formed or not llm.enabled():
        return beliefs
    lines = []
    for b in formed:
        cited = "; ".join(f"{c}={facts_by_id[c]['value']!r}" for c in b["cites"] if c in facts_by_id)
        lines.append(f"- {b['id']} = {b['value']} (score {b['score']}). Cited facts: {cited}")
    result = llm.ask_json(
        "You are an independent auditor. For each belief, decide only from its cited facts whether the belief is "
        "supported. Do not use outside assumptions. Disagree when the facts point the other way or are too thin.",
        "\n".join(lines), _JUDGE_SCHEMA, max_tokens=1500)
    if not result:
        return beliefs
    verdicts = {v["belief_id"]: v for v in result.get("verdicts", [])}
    for b in formed:
        v = verdicts.get(b["id"])
        if v:
            b["judge"] = {"agrees": v["agrees"], "note": v["note"]}
            if not v["agrees"]:
                b["status"] = "needs_review"
    return beliefs
