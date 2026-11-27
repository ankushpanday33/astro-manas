"""Digital twin: rehearse the message on the customer's twin before sending it (idea from MiroFish).

Every candidate action (channel x window x tone) gets an evidence-weighted score from a metric ladder,
most outcome-proximate rung first: conversion within 3 days, then reply, read, delivery. A rung is used only
with enough sends; otherwise the population prior carries it and the candidate is marked cold-start.
When Claude is on, the top candidates are also role-played by an agent built from the customer's persona,
and its simulated reaction is blended in at a fixed, visible weight.
"""
from __future__ import annotations

from typing import Any

from . import llm, privacy

LADDER = [("converted_3d", 1.0), ("replied", 0.5), ("read", 0.3), ("delivered", 0.1)]
MIN_SENDS = 3
PRIOR_STRENGTH = 4.0
SIM_WEIGHT = 0.3
# A slot this customer has never seen must beat their own evidence by 2x to be chosen.
POP_DISCOUNT = 0.5


def population_stats(brains: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, int]]]:
    pop: dict[str, dict[str, dict[str, int]]] = {}
    for b in brains:
        for ch, ws in b.get("comm_stats", {}).items():
            for w, c in ws.items():
                cell = pop.setdefault(ch, {}).setdefault(w, {"sends": 0, "delivered": 0, "read": 0, "replied": 0, "converted_3d": 0})
                for k in cell:
                    cell[k] += c.get(k, 0)
    return pop


def _cell_score(cust: dict[str, int] | None, pop: dict[str, int] | None) -> dict[str, Any]:
    cust = cust or {}
    pop = pop or {}
    for rung, weight in LADDER:
        n, k = cust.get("sends", 0), cust.get(rung, 0)
        pn, pk = pop.get("sends", 0), pop.get(rung, 0)
        if n >= MIN_SENDS and (k > 0 or rung == LADDER[-1][0]):
            prior = pk / pn if pn else 0.2
            post = (prior * PRIOR_STRENGTH + k) / (PRIOR_STRENGTH + n)
            return {"score": post * weight, "rate": round(post, 3), "rung": rung, "weight": weight, "evidence_n": n,
                    "source": "customer", "detail": f"{k}/{n} sends led to {rung.replace('_', ' ')} (shrunk toward population {prior:.0%})"}
    for rung, weight in LADDER:
        pn, pk = pop.get("sends", 0), pop.get(rung, 0)
        if pn >= 20 and pk > 0:
            rate = pk / pn
            return {"score": rate * weight * POP_DISCOUNT, "rate": round(rate, 3), "rung": rung, "weight": weight, "evidence_n": cust.get("sends", 0),
                    "source": "population",
                    "detail": f"exploration: never tried on this customer; population {pk}/{pn} sends led to {rung.replace('_', ' ')} (discounted {int((1 - POP_DISCOUNT) * 100)}%)"}
    return {"score": 0.0, "rate": None, "rung": None, "weight": 0, "evidence_n": 0, "source": "none", "detail": "no evidence anywhere"}


CHART_OFFERS = {"topic_reading", "planet_puja", "personality_report", "name_correction"}
PAID_OFFERS = {"astrologer_consult", "planet_puja", "topic_reading", "personality_report", "resume_checkout"}


def _tone_mods(pack_id: str, fv: dict[str, Any], beliefs: dict[str, dict], tone: str) -> list[tuple[str, float]]:
    """Persona fit for each offer. Every adjustment is a named, visible reason."""
    mods: list[tuple[str, float]] = []
    eng = beliefs.get("engagement", {}).get("value")
    intent = beliefs.get("purchase_intent", {}).get("value")
    anxious = bool(fv.get("anxiety_flag"))
    if tone == "resume_checkout" and not fv.get("abandoned_checkout"):
        return [("nothing left in checkout", -1.0)]
    if tone in CHART_OFFERS and not fv.get("astro_consent"):
        return [("needs a computed chart, and there is no birth-data consent", -1.0)]
    if tone == "personality_report" and not fv.get("nakshatra"):
        return [("needs the birth Panchang, and the birth time is unknown", -1.0)]
    if tone == "daily_horoscope" and eng in {"low", "medium"}:
        mods.append(("drifting or casual user: a light daily touch brings them back", 0.07))
    if tone == "daily_horoscope" and eng == "high":
        mods.append(("already reads the daily horoscope on their own", -0.04))
    if tone == "topic_reading" and fv.get("main_topic"):
        mods.append((f"their chats keep returning to {fv['main_topic']}", 0.08))
    if tone in {"topic_reading", "astrologer_consult"} and fv.get("upcoming_event"):
        mods.append((f"something important is coming up: {fv['upcoming_event']}", 0.05))
    if tone == "astrologer_consult" and intent == "high":
        mods.append(("buys consults and chats with astrologers", 0.06))
    if tone in {"astrologer_consult", "planet_puja"} and anxious:
        mods.append(("sounds anxious: a paid push can feel like pressure", -0.06))
    if tone == "planet_puja" and fv.get("favourite_product") == "planet_puja":
        mods.append(("has booked a puja before", 0.07))
    if tone == "personality_report" and intent in {"low", "medium"} and eng != "low":
        mods.append(("curious, low spend: a report is an easy first step", 0.05))
    if tone == "name_correction" and fv.get("main_topic") is None:
        mods.append(("no pressing topic: a playful feature fits", 0.02))
    # In-app events
    if tone == "resume_checkout":
        mods.append((f"left {str(fv['abandoned_checkout']).replace('_', ' ')} halfway in checkout", 0.12))
    if tone in {"astrologer_consult", "topic_reading"} and (fv.get("cta_clicks_7d") or 0) >= 2:
        mods.append((f"clicked CTAs {fv['cta_clicks_7d']} times this week", 0.04))
    # Installed-app signals (personalise tier only; protect tier can only subtract)
    from .astro import app_catalog
    label_to_cat = {c["label"]: k for k, c in app_catalog.CATEGORIES.items()}
    for lab in fv.get("app_interests") or []:
        cat = label_to_cat.get(lab)
        boost = app_catalog.CATEGORIES.get(cat, {}).get("offer_boost", {}).get(tone)
        if boost:
            mods.append((f"apps: {lab}", boost))
    if tone == "topic_reading" and not fv.get("main_topic") and fv.get("app_topic_hint"):
        mods.append((f"apps point to {fv['app_topic_hint']}", 0.03))
    if tone in PAID_OFFERS and (fv.get("money_pressure_flag") or fv.get("gaming_exposure_flag")):
        mods.append(("protect only: instant-loan or betting app installed, no paid push", -0.12))
    return mods


def _slot_mods(fv: dict[str, Any], channel: str, window: str) -> list[tuple[str, float]]:
    mods = []
    if fv.get("stated_time_preference") == window:
        mods.append((f"they asked to hear from us in the {window}", 0.06))
    if fv.get("active_window") == window and channel in {"push", "in_app"}:
        mods.append((f"usually in the app in the {window}", 0.05))
    if fv.get("contact_objection_flag") and channel in {"push", "whatsapp"}:
        mods.append(("asked us to stop messaging", -0.2))
    return mods


_SIM_SCHEMA = {
    "type": "object",
    "properties": {
        "reactions": {"type": "array", "items": {"type": "object", "properties": {
            "candidate_index": {"type": "integer"},
            "probability_of_acting": {"type": "number", "description": "0 to 1: chance this person pays or renews within 3 days after this message"},
            "inner_reaction": {"type": "string", "description": "One line, in the person's own voice and language"},
        }}}
    },
}


def simulate(brain: dict[str, Any], pack: dict[str, Any], pop: dict[str, Any], render_message, allowed: set[str] | None = None) -> dict[str, Any]:
    fv = {f["id"]: f["value"] for f in brain["facts"]}
    beliefs = {b["id"]: b for b in brain["beliefs"]}
    cust_stats = brain.get("comm_stats", {})
    candidates = []
    for ch in pack["channels"]:
        if allowed is not None and ch not in allowed:
            continue
        for w in pack["windows"]:
            base = _cell_score(cust_stats.get(ch, {}).get(w), pop.get(ch, {}).get(w))
            for tone in pack["tones"]:
                mods = _slot_mods(fv, ch, w) + _tone_mods(brain["pack"], fv, beliefs, tone)
                if any(d <= -1.0 for _, d in mods):
                    continue  # offer not possible for this user (no chart, no Panchang)
                score =max(0.0, base["score"] + sum(m for _, m in mods))
                candidates.append({"channel": ch, "window": w, "tone": tone, "score": round(score, 4),
                                   "empirical": base, "modifiers": [{"why": t, "delta": d} for t, d in mods], "simulated": None})
    candidates.sort(key=lambda c: c["score"], reverse=True)
    top = candidates[:4]

    sim_used = False
    if llm.enabled() and top:
        persona = brain["persona"]
        listing = "\n".join(f"[{i}] {c['channel']} in the {c['window']}, message: \"{render_message(c['tone'], scrub=True)}\""
                            for i, c in enumerate(top))
        out = llm.ask_json(
            "You are role-playing one real customer as a simulation agent. Stay strictly inside the persona and facts. "
            "For each candidate message, estimate how likely this person is to engage deeply or buy within 3 days, and give "
            "their one-line inner reaction in their own language.",
            f"Persona: {privacy.pseudonymise(persona, [brain.get('display_name', '')])}\n"
            f"Beliefs: { {k: v['value'] for k, v in beliefs.items()} }\n\nCandidates:\n{listing}",
            _SIM_SCHEMA, max_tokens=1500)
        if out:
            for r in out.get("reactions", []):
                i = r.get("candidate_index")
                if isinstance(i, int) and 0 <= i < len(top):
                    p = max(0.0, min(1.0, float(r.get("probability_of_acting", 0))))
                    top[i]["simulated"] = {"probability": round(p, 2), "reaction": r.get("inner_reaction", "")}
                    top[i]["score"] = round((1 - SIM_WEIGHT) * top[i]["score"] + SIM_WEIGHT * p, 4)
                    sim_used = True
            top.sort(key=lambda c: c["score"], reverse=True)

    total_sends = sum(c.get("sends", 0) for ws in cust_stats.values() for c in ws.values())
    status = "ok" if top and top[0]["empirical"]["source"] == "customer" else \
        "cold_start" if top and top[0]["empirical"]["source"] == "population" else "insufficient_evidence"
    return {
        "status": status,
        "customer_sends": total_sends,
        "ladder": [{"rung": r, "weight": w} for r, w in LADDER],
        "candidates": top + candidates[4:12],
        "simulation_used": sim_used,
        "sim_weight": SIM_WEIGHT if sim_used else 0,
        "note": {"ok": "Chosen on this customer's own outcomes.",
                 "cold_start": "Not enough of this customer's history: the population prior decides, discounted 50%.",
                 "insufficient_evidence": "No evidence for any channel yet: hold or ask a human."}[status],
    }
