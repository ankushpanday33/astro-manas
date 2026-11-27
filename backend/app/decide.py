"""Decision pipeline: brain -> guards -> twin -> council -> timing -> one decision with its receipts.

Every user is assigned once, deterministically, to treatment or a 10% holdout that gets no message, so uplift is
measured, not claimed. Timing follows PRD 5.7: prefer a send date whose day root is one of the user's lucky numbers.
"""
from __future__ import annotations

import hashlib
import random
from datetime import date, datetime, time, timedelta
from typing import Any

from . import council, privacy, store, twin
from .astro import config as AC
from .astro.config import PLANET_NAME
from .packs import ASTROLOGERS, get_pack

HOLDOUT_PCT = 10
LUCKY_LOOKAHEAD_DAYS = 3


def arm_for(customer_id: str) -> str:
    return "holdout" if int(hashlib.sha256(customer_id.encode()).hexdigest(), 16) % 100 < HOLDOUT_PCT else "treatment"


def _yes(v: Any) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def policy_checks(brain: dict[str, Any], pack: dict[str, Any], today: date) -> tuple[set[str], list[dict[str, Any]], str | None]:
    prof = brain["profile"]
    fv = {f["id"]: f["value"] for f in brain["facts"]}
    checks, allowed = [], set()
    for ch in pack["channels"]:
        key = {"whatsapp": "consent_whatsapp", "push": "consent_push"}.get(ch)
        ok = True if ch == "in_app" else _yes(prof.get(key))
        checks.append({"check": "channel consent", "channel": ch, "passed": ok, "detail": f"{key or 'in-app card'} = {prof.get(key, 'always on')}"})
        if ok:
            allowed.add(ch)
    checks.append({"check": "birth-data consent", "passed": bool(prof.get("astro_consent_at")),
                   "detail": "chart computed from consented data" if prof.get("astro_consent_at") else "no consent: chart-based offers are switched off (PRD 5.8)"})
    cap = pack["frequency_cap"]
    week = fv.get("contacts_last_7d") or 0
    capped = week >= cap["per_week"]
    checks.append({"check": "frequency cap", "passed": not capped, "detail": f"{week} messages in 7 days, cap {cap['per_week']}"})
    checks.append({"check": "quiet hours", "passed": True, "detail": pack["quiet_hours_note"]})
    checks.append({"check": "gemstones", "passed": True, "detail": "never prescribed: traditional association only, REQUIRES_KUNDLI_REVIEW"})
    if fv.get("app_signal_consent"):
        prot = [x for x, on in (("instant loan", fv.get("money_pressure_flag")), ("betting", fv.get("gaming_exposure_flag"))) if on]
        checks.append({"check": "app signals", "passed": True,
                       "detail": ("protect-only signals present (" + ", ".join(prot) + "): paid offers switched off" if prot
                                  else "used to personalise only; discarded categories were never stored")})
    else:
        checks.append({"check": "app signals", "passed": True, "detail": "no app-signal consent: installed apps ignored"})
    block = None
    if fv.get("contact_objection_flag"):
        block = "hold"
        checks.append({"check": "opt-out", "passed": False, "detail": "they asked us to stop messaging"})
    if capped and not block:
        block = "hold"
    if not allowed and not block:
        block = "hold"
    return allowed, checks, block


def converts_anyway(brain: dict[str, Any]) -> str | None:
    """Uplift guard: a devoted daily user opens the app on their own; a message would only add noise."""
    fv = {f["id"]: f["value"] for f in brain["facts"]}
    if (fv.get("sessions_7d") or 0) >= 6 and (fv.get("days_since_last_session") or 99) <= 1 and not fv.get("upcoming_event"):
        return f"opens the app daily on their own ({fv['sessions_7d']} times this week): a message would not change the outcome."
    return None


def match_astrologer(brain: dict[str, Any]) -> dict[str, Any] | None:
    """PRD 5.7: suggest astrologers who specialise in the user's nakshatra lord or radical planet; topic breaks ties."""
    chart = brain.get("chart") or {}
    fv = {f["id"]: f["value"] for f in brain["facts"]}
    planets = [p for p in (chart.get("nakshatra_lord"), chart.get("radical_planet")) if p]
    best, best_score = None, 0
    for a in ASTROLOGERS:
        score = sum(2 if p in a["planets"] else 0 for p in planets[:1]) + sum(1 for p in planets[1:] if p in a["planets"])
        score += 1 if fv.get("main_topic") in a["topics"] else 0
        if score > best_score:
            best, best_score = a, score
    if not best:
        return None
    hits = [p for p in planets if p in best["planets"]]
    topic = fv.get("main_topic") if fv.get("main_topic") in best["topics"] else None
    return {**best, "why": "specialises in " + " and ".join([", ".join(hits)] * bool(hits) + [topic] * bool(topic))}


def copy_check(text: str) -> list[str]:
    low = text.lower()
    return [w for w in AC.BANNED_COPY if w in low]


def render_values(brain: dict[str, Any], scrub: bool = False) -> dict[str, Any]:
    chart = brain.get("chart") or {}
    fv = {f["id"]: f["value"] for f in brain["facts"]}
    astro = match_astrologer(brain)
    planet = chart.get("radical_planet") or ""
    return dict(
        name="{name}" if scrub else brain.get("display_name", "").split(" ")[0],
        nakshatra=chart.get("nakshatra_name") or "your", topic=fv.get("main_topic") or fv.get("app_topic_hint") or "life",
        planet=planet.title(), planet_name=PLANET_NAME.get(planet, planet.title()), radical=chart.get("radical_number", ""),
        astrologer=astro["name"] if astro else "an astrologer", title=chart.get("personality_title") or "your profile",
        name_number=chart.get("name_number", ""), link="astro.link/xyz",
        checkout_item=str(fv.get("abandoned_checkout") or "your booking").replace("_", " "))


def make_renderer(brain: dict[str, Any], pack: dict[str, Any]):
    def render(tone: str, scrub: bool = False) -> str:
        return pack["templates"][tone].format(**render_values(brain, scrub))
    return render


def delivery_plan(brain: dict[str, Any], chosen: dict[str, Any], allowed: set[str]) -> dict[str, Any]:
    """Platform, fallback, language, script and channel-shaped copy for the chosen action."""
    from . import llm, messaging

    recs = store.records_for(brain["customer_id"])
    texts = [c.get("text", "") for c in recs.get("chats", [])] + \
            [c.get("reply_text", "") for c in recs.get("communications", []) if c.get("direction") == "in"]
    plan = messaging.plan(chosen["channel"], chosen["tone"], brain["profile"].get("preferred_language"), [t for t in texts if t],
                          render_values(brain), recs.get("communications", []), allowed)
    msg = plan["message"]
    if msg["translation_needed"] and llm.enabled():
        out = llm.ask_json("Translate this short app notification into the target language, natural and respectful. Keep names, numbers, "
                           "Nakshatra and planet names and the link exactly. No new claims, no urgency, no fear.",
                           f"Target: {plan['language']['template_language']}\nText: {msg['body']}",
                           {"type": "object", "properties": {"text": {"type": "string"}}}, max_tokens=600)
        if out and out.get("text") and not copy_check(out["text"]):
            msg.update(body=out["text"], template_language=plan["language"]["template_language"], translation_needed=False,
                       note=f"translated by {llm.MODEL}; review before registering the template")
    return plan


def lucky_send_date(window: str, pack: dict[str, Any], now: datetime, lucky: list[int], before: date | None) -> tuple[datetime, str]:
    """Earliest slot in the next few days whose day root ((day - 1) % 9 + 1) is a lucky number; else the earliest slot."""
    start_h, end_h = pack["windows"][window]
    first = now.date() if now.hour < end_h - 1 else now.date() + timedelta(days=1)
    soonest = now.replace(second=0, microsecond=0) + timedelta(minutes=10)

    def slot(day: date) -> datetime:
        at = datetime.combine(day, time(start_h, 30))
        return max(at, soonest) if day == now.date() else at

    for offset in range(LUCKY_LOOKAHEAD_DAYS + 1):
        day = first + timedelta(days=offset)
        if before and day >= before:
            break
        root = (day.day - 1) % 9 + 1
        if root in (lucky or []):
            return slot(day), f"{day.strftime('%d/%m/%Y')} has day root {root}, one of their lucky numbers {lucky}"
    if not lucky:
        return slot(first), "no chart, so the earliest slot"
    if before:
        return slot(first), "no lucky-root day before their event, so the earliest slot"
    return slot(first), f"no lucky-root day in the next {LUCKY_LOOKAHEAD_DAYS} days, so the earliest slot"


def decide(customer_id: str, use_llm: bool = True, now: datetime | None = None, pop: dict[str, Any] | None = None) -> dict[str, Any]:
    brain = store.get_brain(customer_id)
    if not brain:
        raise KeyError(customer_id)
    now = now or datetime.now()
    pack = get_pack(brain["pack"])
    today = date.fromisoformat(brain["as_of"])
    arm = arm_for(customer_id)
    render = make_renderer(brain, pack)
    fv = {f["id"]: f["value"] for f in brain["facts"]}

    allowed, checks, block = policy_checks(brain, pack, today)
    anyway = converts_anyway(brain)
    checks.append({"check": "uplift guard", "passed": anyway is None, "detail": anyway or "a message is expected to change the outcome"})
    if anyway and not block:
        block = "no_action"
    pop = pop if pop is not None else twin.population_stats(store.all_brains())
    sim = twin.simulate(brain, pack, pop, render, allowed=allowed)
    debate = council.deliberate(brain, sim, use_llm=use_llm and not block)

    mod = debate["moderator"]
    action = block or mod["action"]
    chosen = sim["candidates"][mod["choice"]] if action == "contact" and mod.get("choice") is not None else None
    if action == "contact" and sim["status"] == "insufficient_evidence":
        action, chosen = "human_review", None

    decision: dict[str, Any] = {
        "customer_id": customer_id, "alias": brain["alias"], "pack": brain["pack"],
        "created_at": now.isoformat(timespec="seconds"), "arm": arm, "action": action, "sent": False,
        "channel": chosen["channel"] if chosen else None, "window": chosen["window"] if chosen else None,
        "tone": chosen["tone"] if chosen else None, "offer": chosen["tone"] if chosen else None,
        "language": brain["persona"].get("language"), "send_at": None, "timing_reason": None, "message_preview": None,
        "astrologer": match_astrologer(brain) if chosen and chosen["tone"] == "astrologer_consult" else None,
        "confidence": None, "confidence_meaning": "sample adequacy: how much of this user's own evidence backs the choice",
        "policy_checks": checks, "twin": sim, "council": debate,
    }
    if chosen:
        ev = fv.get("upcoming_event") or ""
        before = None
        if " on " in ev:
            try:
                before = datetime.strptime(ev.split(" on ")[-1], "%d/%m/%Y").date()
            except ValueError:
                before = None
        lucky = (brain.get("chart") or {}).get("lucky_numbers") or []
        at, why = lucky_send_date(chosen["window"], pack, now, lucky, before if before and before > today else None)
        decision["send_at"], decision["timing_reason"] = at.isoformat(timespec="minutes"), why
        plan = delivery_plan(brain, chosen, allowed)
        decision["delivery"] = plan
        msg = plan["message"]["body"] or render(chosen["tone"])
        bad = copy_check(msg) + copy_check(render(chosen["tone"]))
        checks.append({"check": "responsible copy", "passed": not bad,
                       "detail": f"blocked words: {bad}" if bad else "traditional guidance wording, no fear, no guarantees"})
        if bad:
            decision.update(action="human_review", channel=None, window=None, tone=None, offer=None, send_at=None)
            chosen = None
        else:
            decision["message_preview"] = msg
            decision["confidence"] = round(min(1.0, chosen["empirical"]["evidence_n"] / 12), 2) if chosen["empirical"]["source"] == "customer" else 0.15
    if arm == "holdout":
        decision["holdout_note"] = "Holdout arm: decided but deliberately not sent, so uplift can be measured against it."
    if decision.get("delivery") and chosen:
        dl = decision["delivery"]
        checks.append({"check": "platform", "passed": True,
                       "detail": f"{dl['provider']['name'] if dl['provider'] else 'no platform'} for {dl['channel']}"
                                 + (f", fallback {dl['fallback']['channel']}" if dl.get("fallback") else "")
                                 + f"; language {dl['language']['template_language']} ({dl['language']['why']})"})
    decision["reason"] = _reason(decision, brain, chosen, mod)
    decision["receipts"] = _receipts(brain, decision, chosen)
    decision["decision_id"] = store.save_decision(customer_id, decision["created_at"], arm, decision)
    return decision


def _reason(decision: dict[str, Any], brain: dict[str, Any], chosen: dict[str, Any] | None, mod: dict[str, Any]) -> str:
    if decision["action"] == "no_action":
        return "No message: " + next(c["detail"] for c in decision["policy_checks"] if c["check"] == "uplift guard")
    if decision["action"] == "hold":
        failing = [c["detail"] for c in decision["policy_checks"] if not c["passed"]]
        return "Hold: " + ("; ".join(failing) if failing else mod.get("summary", "no evidenced channel"))
    if decision["action"] == "human_review":
        return "Human review: " + mod.get("summary", "not enough evidence to act alone")
    mods = "; ".join(m["why"] for m in chosen["modifiers"])
    sim = f" Twin reaction: \"{chosen['simulated']['reaction']}\"." if chosen.get("simulated") else ""
    astro = f" Matched {decision['astrologer']['name']} ({decision['astrologer']['why']})." if decision.get("astrologer") else ""
    dl = decision.get("delivery") or {}
    via = f" via {dl['provider']['name']}" if dl.get("provider") else ""
    lang = dl.get("language", {}).get("template_language") or decision["language"]
    return (f"{chosen['tone'].replace('_', ' ').capitalize()} on {chosen['channel'].replace('_', '-')}{via} in the {chosen['window']}, in {lang}. "
            f"{chosen['empirical']['detail']}.{(' ' + mods + '.') if mods else ''}{astro}{sim} Timing: {decision['timing_reason']}. {mod.get('summary', '')}")


def _receipts(brain: dict[str, Any], decision: dict[str, Any], chosen: dict[str, Any] | None) -> list[dict[str, Any]]:
    facts = {f["id"]: f for f in brain["facts"]}
    cited = [b for b in brain["beliefs"] if b["status"] != "insufficient_evidence"]
    fact_ids = sorted({c for b in cited for c in b["cites"] if c in facts})
    chart = brain.get("chart") or {}
    keys = ("radical_number", "destiny_number", "name_number", "lucky_numbers", "nakshatra_name", "personality_title")
    return [
        {"stage": "chart", "items": [f"{k} = {chart[k]}" for k in keys if chart.get(k) is not None] or ["no chart: consent missing"]},
        {"stage": "world", "items": [brain["world"]["summary"]]},
        {"stage": "memory", "items": [f"{m['kind']}{': ' + m['detail'] if m.get('detail') else ''} (written {m['written_on']})" for m in brain["memory"]]},
        {"stage": "facts", "items": [f"{fid} = {facts[fid]['value']!r}: {facts[fid]['formula']}" for fid in fact_ids]},
        {"stage": "beliefs", "items": [f"{b['id']} = {b['value']} (confidence {b['confidence']})" for b in cited]},
        {"stage": "twin", "items": [f"{c['channel']} · {c['window']} · {c['tone']}: score {c['score']}" for c in decision["twin"]["candidates"][:3]]},
        {"stage": "council", "items": [decision["council"]["moderator"].get("summary", "")]},
        {"stage": "decision", "items": [decision["reason"]]},
    ]


def simulate_outcomes(seed: int = 7) -> dict[str, Any]:
    """DEMO ONLY: draw outcomes for the latest decisions so the uplift view has something to show.

    Treatment converts at the chosen candidate's evidence-weighted rate; holdout at a self-cure rate derived from
    each user's own engagement. Results are flagged simulated everywhere they appear.
    """
    rng = random.Random(seed)
    latest = store.latest_decisions()
    with store.db() as conn:
        conn.execute("DELETE FROM outcomes WHERE simulated=1")
    n = 0
    for cid, d in latest.items():
        brain = store.get_brain(cid)
        if not brain:
            continue
        fv = {f["id"]: f["value"] for f in brain["facts"]}
        eng = next((b["score"] or 0 for b in brain["beliefs"] if b["id"] == "engagement"), 0)
        self_cure = 0.08 + 0.75 * eng
        if d["arm"] == "holdout" or d["action"] != "contact":
            p = self_cure
        else:
            top = d["twin"]["candidates"][0] if d["twin"]["candidates"] else {"score": 0}
            p = self_cure + (1 - self_cure) * min(0.8, 1.2 * top["score"])
        store.record_outcome(cid, d["decision_id"], d["arm"], rng.random() < p, datetime.now().isoformat(timespec="seconds"), True)
        n += 1
    return {"simulated_outcomes": n}


def uplift() -> dict[str, Any]:
    s = store.outcome_summary()
    t, h = s.get("treatment", {"n": 0, "converted": 0}), s.get("holdout", {"n": 0, "converted": 0})
    tr = t["converted"] / t["n"] if t["n"] else None
    hr = h["converted"] / h["n"] if h["n"] else None
    return {"treatment": {**t, "rate": tr}, "holdout": {**h, "rate": hr},
            "uplift_pts": round((tr - hr) * 100, 1) if tr is not None and hr is not None else None,
            "simulated": any(x.get("simulated") for x in s.values()),
            "note": "Uplift = treatment conversion minus holdout conversion. Holdout is a fixed 10% that is never messaged."}


def ask(customer_id: str, question: str) -> dict[str, Any]:
    """Plain-language question over one brain. Answers cite fact and belief ids."""
    from . import llm

    brain = store.get_brain(customer_id)
    if not brain:
        raise KeyError(customer_id)
    if llm.enabled():
        digest = privacy.pseudonymise({"facts": [{k: f[k] for k in ("id", "question", "value", "formula")} for f in brain["facts"]],
                                       "beliefs": [{k: b[k] for k in ("id", "value", "status", "reasoning")} for b in brain["beliefs"]],
                                       "chart": brain.get("chart"), "memory": brain["memory"], "persona": brain["persona"],
                                       "latest_decision": (store.latest_decision(customer_id) or {}).get("reason")},
                                      [brain.get("display_name", "")])
        out = llm.ask_json("Answer questions about one astrology-app user using only the brain given. Never invent chart values. Cite fact and belief ids. "
                           "If the brain does not contain the answer, say so plainly.",
                           f"Brain: {digest}\n\nQuestion: {question}",
                           {"type": "object", "properties": {"answer": {"type": "string"}, "cites": {"type": "array", "items": {"type": "string"}}}},
                           max_tokens=1200)
        if out:
            return {**out, "method": "llm"}
    q = set(question.lower().replace("?", "").split())
    scored = sorted(brain["facts"], key=lambda f: -len(q & set((f["question"] + " " + f["id"].replace("_", " ")).lower().split())))
    hits = [f for f in scored[:3] if q & set((f["question"] + " " + f["id"].replace("_", " ")).lower().split())]
    if not hits:
        return {"answer": "I could not match that question to a fact in this brain. Turn on Claude for open questions.", "cites": [], "method": "rules"}
    return {"answer": " ".join(f"{f['question']} {f['value']!r} ({f['formula']})." for f in hits), "cites": [f["id"] for f in hits], "method": "rules"}
