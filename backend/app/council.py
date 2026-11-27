"""Decision council: three agents with different goals argue, a moderator decides (idea from BettaFish's ForumEngine).

  Engagement Analyst  - wants the user back and engaged: picks the best evidence-weighted candidate
  Wellbeing Advocate  - protects the user: least intrusive option, no paid push to an anxious user, vetoes on opt-out
  Value Strategist    - wants the most expected value per rupee of channel spend (offer value x chance / cost)

Disagreement is kept, not hidden: the moderator's summary names who dissented and why.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from . import llm, privacy

CHANNEL_COST_INR = {"whatsapp": 0.12, "push": 0.01, "in_app": 0.0, "sms": 0.15}
INTRUSION = {"in_app": 0, "push": 1, "whatsapp": 2, "sms": 2}
# Expected value of each offer when it lands (₹). Free offers carry a small engagement value.
OFFER_VALUE_INR = {"astrologer_consult": 299, "planet_puja": 501, "topic_reading": 199, "personality_report": 99,
                   "daily_horoscope": 5, "name_correction": 3, "resume_checkout": 250}
PAID = {"astrologer_consult", "planet_puja", "topic_reading", "personality_report", "resume_checkout"}

AGENTS = {
    "outcome_analyst": ("Engagement Analyst", "You want the user engaged. Back the candidate with the strongest evidence of working for this person."),
    "customer_advocate": ("Wellbeing Advocate", "You protect the user. Prefer the least intrusive option that still works. Never push a paid "
                                                "offer to an anxious user. Veto any message if they asked us to stop. Copy must be traditional guidance, never fear."),
    "cost_strategist": ("Value Strategist", "You want the most expected value per rupee of channel spend: offer value times chance, divided by cost."),
}


def _label(c: dict[str, Any]) -> str:
    return f"{c['channel']} · {c['window']} · {c['tone']}"


def _rules(brain: dict[str, Any], cands: list[dict[str, Any]]) -> dict[str, Any]:
    fv = {f["id"]: f["value"] for f in brain["facts"]}
    top_score = cands[0]["score"] if cands else 0
    # Alternatives only count if they are nearly as good AND backed by this user's own evidence.
    viable = [i for i, c in enumerate(cands)
              if c["score"] >= 0.9 * top_score and (c["empirical"]["source"] == "customer" or i == 0)] or [0]
    gentle_pool = [i for i, c in enumerate(cands) if c["score"] >= 0.7 * top_score] or [0]

    analyst = {"speaker": "outcome_analyst", "choice": 0,
               "argument": f"{_label(cands[0])} has the strongest evidence: {cands[0]['empirical']['detail']}.",
               "cites": ["best_responding_slot", "active_window"]}

    protect_reason = "sounds anxious" if fv.get("anxiety_flag") else "an instant-loan app is installed" if fv.get("money_pressure_flag") \
        else "a real-money gaming app is installed" if fv.get("gaming_exposure_flag") else None
    anxious = bool(protect_reason)
    pool = [i for i in gentle_pool if cands[i]["tone"] not in PAID] if anxious else viable
    # For an anxious user the calm daily guidance comes first; then the least intrusive channel.
    advocate_choice = min(pool or viable, key=lambda i: (anxious and cands[i]["tone"] != "daily_horoscope",
                                                          INTRUSION.get(cands[i]["channel"], 2), -cands[i]["score"]))
    veto = "they asked us to stop messaging: respect it" if fv.get("contact_objection_flag") else None
    why = (f"{protect_reason}, so calm guidance and no paid offer: " if anxious else "") + f"{_label(cands[advocate_choice])} is the least intrusive option that still works."
    advocate = {"speaker": "customer_advocate", "choice": advocate_choice, "veto": veto, "argument": veto or why,
                "cites": ["anxiety_flag", "contact_objection_flag"], "protect": anxious}

    def ev(i: int) -> float:
        c = cands[i]
        return c["score"] * OFFER_VALUE_INR.get(c["tone"], 1) / (CHANNEL_COST_INR.get(c["channel"], 0.05) + 0.05)

    strategist_choice = max(viable, key=ev)
    c = cands[strategist_choice]
    strategist = {"speaker": "cost_strategist", "choice": strategist_choice,
                  "argument": f"{_label(c)} has the best expected value: ₹{OFFER_VALUE_INR.get(c['tone'], 0)} offer x {c['score']:.2f} chance, "
                              f"₹{CHANNEL_COST_INR.get(c['channel'], 0):.2f} per send.",
                  "cites": ["purchase_intent", "spend_90d"]}
    return {"analyst": analyst, "advocate": advocate, "strategist": strategist}


def _moderate(stances: list[dict[str, Any]], cands: list[dict[str, Any]]) -> dict[str, Any]:
    veto = next((s.get("veto") for s in stances if s.get("veto")), None)
    if veto:
        return {"choice": None, "action": "hold", "summary": f"Wellbeing Advocate vetoed: {veto}.",
                "dissent": [s["speaker"] for s in stances if not s.get("veto")]}
    votes: dict[int, list[str]] = {}
    for s in stances:
        votes.setdefault(s["choice"], []).append(s["speaker"])
    best = max(votes, key=lambda i: (len(votes[i]), cands[i]["score"]))
    adv = next((s for s in stances if s["speaker"] == "customer_advocate"), None)
    # Wellbeing override: an anxious user is not sold to, as long as the gentle option is still reasonably strong.
    if adv and adv.get("protect") and cands[best]["tone"] in PAID and adv["choice"] != best             and cands[adv["choice"]]["score"] >= 0.6 * cands[best]["score"]:
        overruled = [s["speaker"] for s in stances if s["choice"] == best]
        return {"choice": adv["choice"], "action": "contact",
                "summary": f"Wellbeing override: protect-only signal, so {_label(cands[adv['choice']])} instead of the paid "
                           f"{cands[best]['tone'].replace('_', ' ')} backed by {', '.join(overruled)}.", "dissent": overruled}
    dissent = [s["speaker"] for s in stances if s["choice"] != best]
    return {"choice": best, "action": "contact",
            "summary": f"{len(votes[best])} of 3 agents back {_label(cands[best])}" + (f"; dissent from {', '.join(dissent)}." if dissent else "; unanimous."),
            "dissent": dissent}


_STANCE_SCHEMA = {"type": "object", "properties": {
    "choice": {"type": "integer", "description": "index of the candidate you back"},
    "veto": {"type": ["string", "null"], "description": "only if no candidate should be sent: the reason a human must take over"},
    "argument": {"type": "string", "description": "two sentences at most, citing fact ids"},
    "cites": {"type": "array", "items": {"type": "string"}},
}}
_MOD_SCHEMA = {"type": "object", "properties": {
    "choice": {"type": ["integer", "null"]},
    "action": {"type": "string", "enum": ["contact", "human_review", "hold"]},
    "summary": {"type": "string"},
    "dissent": {"type": "array", "items": {"type": "string"}},
}}


def deliberate(brain: dict[str, Any], twin: dict[str, Any], use_llm: bool = True) -> dict[str, Any]:
    cands = twin["candidates"][:8]
    if not cands:
        return {"method": "rules", "stances": [], "moderator": {"choice": None, "action": "hold", "summary": "No channel is allowed or evidenced.", "dissent": []}}

    rules = _rules(brain, cands)
    if not (use_llm and llm.enabled()):
        stances = [rules["analyst"], rules["advocate"], rules["strategist"]]
        return {"method": "rules", "stances": stances, "moderator": _moderate(stances, cands)}

    names = [brain.get("display_name", "")]
    digest = privacy.pseudonymise({
        "facts": {f["id"]: f["value"] for f in brain["facts"] if f["value"] is not None},
        "beliefs": {b["id"]: {"value": b["value"], "status": b["status"]} for b in brain["beliefs"]},
        "memory": [{"kind": m["kind"], "detail": m.get("detail"), "written_on": m["written_on"]} for m in brain["memory"]],
        "candidates": [{"index": i, "action": _label(c), "score": c["score"], "evidence": c["empirical"]["detail"],
                        "channel_cost_inr": CHANNEL_COST_INR.get(c["channel"]), "simulated": c["simulated"]} for i, c in enumerate(cands)],
    }, names)

    def ask(key: str) -> dict[str, Any]:
        name, role = AGENTS[key]
        out = llm.ask_json(f"You are the {name} on a decision council for customer {brain['alias']}. {role} "
                           "Argue only from the facts given; cite fact ids.", str(digest), _STANCE_SCHEMA, max_tokens=800)
        fallback = {"outcome_analyst": rules["analyst"], "customer_advocate": rules["advocate"], "cost_strategist": rules["strategist"]}[key]
        if not out or not isinstance(out.get("choice"), int) or not 0 <= out["choice"] < len(cands):
            return fallback
        return {"speaker": key, **out}

    with ThreadPoolExecutor(max_workers=3) as pool:
        stances = list(pool.map(ask, AGENTS))

    transcript = "\n".join(f"{AGENTS[s['speaker']][0]}: backs [{s['choice']}] {_label(cands[s['choice']])}. "
                           f"{('VETO: ' + s['veto'] + '. ') if s.get('veto') else ''}{s['argument']}" for s in stances)
    mod = llm.ask_json("You moderate a decision council. Weigh the three arguments. A well-founded veto from the Wellbeing Advocate wins, and an anxious user is never sold a paid offer when a gentle one is reasonably strong. "
                       "Name dissent honestly. Choose a candidate index, or human_review / hold.",
                       f"Candidates: {[_label(c) for c in cands]}\n\n{transcript}", _MOD_SCHEMA, max_tokens=600)
    if not mod or (mod.get("action") == "contact" and not (isinstance(mod.get("choice"), int) and 0 <= mod["choice"] < len(cands))):
        mod = _moderate(stances, cands)
    return {"method": "llm", "stances": stances, "moderator": mod}
