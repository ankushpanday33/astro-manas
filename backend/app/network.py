"""Decision network: the whole reasoning of one decision as a layered graph.

inputs -> chart engine -> facts -> beliefs -> twin candidates -> council -> moderator + guards -> timing -> decision

Every edge is a real dependency in the code (a formula input, a cited fact, a persona-fit rule, a vote).
The 'path' flag marks the nodes and edges that actually led to the final decision.
"""
from __future__ import annotations

from typing import Any

LAYERS = ["Inputs", "Chart engine", "Facts", "Beliefs", "Digital twin", "Council", "Moderator & guards", "Decision"]
CAPTIONS = [
    "What we know: the birth details they consented to share, and what they do in the app.",
    "Deterministic engine (PRD Module A and B): numbers and Panchang computed once and stored on the user row.",
    "Facts computed in code, each with a formula and cited rows.",
    "Beliefs formed only from cited facts. Too little evidence means no belief.",
    "Every offer x channel x time is rehearsed on the user's digital twin and scored.",
    "Three agents with different goals argue over the top candidates.",
    "The moderator decides; guards (consent, opt-out, caps, copy) can stop anything.",
    "One decision, sent on a lucky-number day when possible, with its receipts.",
]

OFFER_BELIEFS = {
    "daily_horoscope": ["engagement"], "topic_reading": ["topic_focus"], "astrologer_consult": ["purchase_intent", "anxiety"],
    "planet_puja": ["purchase_intent", "anxiety", "money_pressure"], "personality_report": ["engagement"], "name_correction": ["engagement"],
    "resume_checkout": ["purchase_propensity", "money_pressure"],
}
OFFER_CHART = {"topic_reading": ["radical"], "planet_puja": ["radical"], "personality_report": ["nakshatra"],
               "name_correction": ["name_number"], "daily_horoscope": ["nakshatra"], "astrologer_consult": ["nakshatra", "radical"]}
FACT_INPUTS = {
    "sessions_7d": "in_sessions", "usage_trend": "in_sessions", "deep_sessions_30d": "in_sessions", "days_since_last_session": "in_sessions",
    "active_window": "in_sessions", "main_topic": "in_chats", "anxiety_flag": "in_chats", "upcoming_event": "in_chats",
    "contact_objection_flag": "in_chats", "chats_60d": "in_chats", "purchases_90d": "in_purchases", "spend_90d": "in_purchases",
    "favourite_product": "in_purchases", "best_responding_slot": "in_messages", "days_since_last_reply": "in_messages",
    "events_30d": "in_events", "cta_clicks_7d": "in_events", "top_cta": "in_events", "abandoned_checkout": "in_events",
    "login_dropoff": "in_events", "purchase_propensity_7d": "in_events", "churn_risk_14d": "in_events",
    "app_interests": "in_apps", "app_topic_hint": "in_apps", "money_pressure_flag": "in_apps", "gaming_exposure_flag": "in_apps",
    "competitor_astro_user": "in_apps", "premium_affinity": "in_apps",
}
FACT_CHART = {"nakshatra": "nakshatra", "lucky_numbers": "lucky", "ruling_planet": "radical"}
SHOW_FACTS = list(FACT_INPUTS) + list(FACT_CHART)


def build(brain: dict[str, Any], decision: dict[str, Any] | None) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    chart = brain.get("chart") or {}
    fv = {f["id"]: f for f in brain["facts"]}

    def node(nid: str, layer: int, label: str, value: Any = None, detail: str = "", kind: str = "") -> None:
        nodes[nid] = {"id": nid, "layer": layer, "label": label, "value": value, "detail": detail, "kind": kind or LAYERS[layer]}

    def edge(a: str, b: str, why: str, w: float = 1.0) -> None:
        if a in nodes and b in nodes:
            edges.append({"from": a, "to": b, "why": why, "weight": round(w, 3)})

    # 0 inputs
    prof = brain["profile"]
    node("in_name", 0, "Name", chart.get("name_number") and "numerology name", "Commonly used English spelling (Chaldean)")
    node("in_dob", 0, "Date of birth", "DD/MM/YYYY", "Drives Radical, Destiny and Lo Shu. Never logged (PRD 5.8)")
    node("in_birth", 0, "Birth time + place", prof.get("birth_time_confidence") or "UNKNOWN",
         "Exact instant in UTC via IANA zone; Panchang needs both")
    for key, label, src in [("in_sessions", "App sessions", "sessions"), ("in_chats", "Astrologer chats", "chats"),
                            ("in_purchases", "Purchases", "purchases"), ("in_messages", "Messages sent", "communications"),
                            ("in_events", "In-app events", "events"), ("in_apps", "Installed apps", "installed_apps")]:
        node(key, 0, label, brain["world"]["counts"].get({"sessions": "Session", "chats": "Chat", "purchases": "Purchase",
                                                         "communications": "Communication", "events": "Event",
                                                         "installed_apps": "InstalledApp"}[src], 0),
             f"rows from {src}" + (" (only with app_signal_consent; discarded categories never stored)" if src == "installed_apps" else ""))

    # 1 chart engine
    if chart:
        node("radical", 1, "Radical (Mulank)", f"{chart['radical_number']} · {chart['radical_planet']}", "((day - 1) % 9) + 1")
        node("destiny", 1, "Destiny (Bhagyank)", f"{chart['destiny_number']} · {chart['destiny_planet']}", "reduce(sum of all DOB digits)")
        node("name_number", 1, "Name number", f"{chart['name_number']} · {chart['name_planet']}", "reduce(Chaldean letter sum)")
        node("lucky", 1, "Lucky numbers", chart.get("lucky_numbers"), "weighted friendship 2/2/1, top tier")
        edge("in_dob", "radical", "birth day")
        edge("in_dob", "destiny", "all DOB digits")
        edge("in_name", "name_number", "Chaldean map")
        for src, w in (("radical", 2), ("destiny", 2), ("name_number", 1)):
            edge(src, "lucky", f"weight {w}", w / 2)
        if chart.get("nakshatra_name"):
            node("nakshatra", 1, "Nakshatra", f"{chart['nakshatra_name']} p{chart['nakshatra_pada']}", f"lord {chart['nakshatra_lord']}, 30% weight")
            node("tithi", 1, "Tithi", chart.get("tithi_name"), "mind and emotions, 20%")
            node("yoga", 1, "Yoga", chart.get("yoga_name"), "thinking style, 20%")
            node("vara", 1, "Vara", chart.get("vara_name"), f"lord {chart.get('vara_lord')}, sunrise rule, 15%")
            node("karana", 1, "Karana", chart.get("karana_name"), "working style, 15%")
            for a in ("nakshatra", "tithi", "yoga", "vara", "karana"):
                edge("in_birth", a, "sidereal Sun and Moon at the birth instant")
        else:
            node("no_panchang", 1, "Panchang skipped", "birth time unknown", "PRD 5.1: Panchang columns stay NULL")
            edge("in_birth", "no_panchang", "time missing")
    else:
        node("consent_gate", 1, "Chart not computed", "no consent", "PRD 5.8: record consent before computing")
        for i in ("in_name", "in_dob", "in_birth"):
            edge(i, "consent_gate", "blocked without consent")

    # 2 facts
    for fid in SHOW_FACTS:
        f = fv.get(fid)
        if not f or f["value"] in (None, False, 0, [], ""):
            continue
        node(f"f_{fid}", 2, f["question"].rstrip("?"), f["value"], f["formula"])
        if fid in FACT_INPUTS:
            edge(FACT_INPUTS[fid], f"f_{fid}", "computed from these rows")
        if fid in FACT_CHART:
            edge(FACT_CHART[fid], f"f_{fid}", "read from the stored user row")

    # 3 beliefs
    for b in brain["beliefs"]:
        node(f"b_{b['id']}", 3, b["id"].replace("_", " ").title(), b["value"] if b["status"] == "formed" else b["status"].replace("_", " "),
             b["reasoning"])
        for c in b["cites"]:
            edge(f"f_{c}", f"b_{b['id']}", "cited fact", 1.0)

    # 4 twin, 5 council, 6 moderator + guards, 7 decision
    chosen_key = None
    if decision:
        allc = decision["twin"]["candidates"]
        backed = {s["choice"] for s in decision["council"]["stances"]}
        shown = [i for i in range(len(allc)) if i < 4 or i in backed]
        for i in shown:
            c = allc[i]
            key = f"c_{i}"
            node(key, 4, c["tone"].replace("_", " ").title(), f"{c['channel'].replace('_', '-')} · {c['window']} · {c['score']}",
                 c["empirical"]["detail"] + ("; " + "; ".join(m["why"] for m in c["modifiers"]) if c["modifiers"] else ""))
            nodes[key]["rank"] = i + 1
            edge("b_reachability", key, "evidence from past sends", c["empirical"]["score"] or 0.2)
            for bid in OFFER_BELIEFS.get(c["tone"], []):
                edge(f"b_{bid}", key, "persona fit")
            for ch in OFFER_CHART.get(c["tone"], []):
                edge(ch, key, "personalised from the chart", 0.6)
            if decision.get("channel") and (c["channel"], c["window"], c["tone"]) == (decision["channel"], decision["window"], decision["tone"]):
                chosen_key = key
        names = {"outcome_analyst": "Engagement Analyst", "customer_advocate": "Wellbeing Advocate", "cost_strategist": "Value Strategist"}
        for s in decision["council"]["stances"]:
            key = f"a_{s['speaker']}"
            node(key, 5, names.get(s["speaker"], s["speaker"]), "veto" if s.get("veto") else f"backs #{s['choice'] + 1}", s.get("veto") or s["argument"])
            edge(f"c_{s['choice']}", key, "backed by", 1.5)
        mod = decision["council"]["moderator"]
        node("moderator", 6, "Moderator", mod.get("action"), mod.get("summary", ""))
        for s in decision["council"]["stances"]:
            edge(f"a_{s['speaker']}", "moderator", "argument")
        failing = [c for c in decision["policy_checks"] if not c["passed"]]
        node("guards", 6, "Guards", "stop" if failing else "all passed",
             "; ".join(f"{c['check']}: {c['detail']}" for c in (failing or decision["policy_checks"][-3:])))
        for f in ("f_contact_objection_flag", "f_anxiety_flag", "f_money_pressure_flag", "f_gaming_exposure_flag"):
            edge(f, "guards", "checked by guard")
        if decision.get("send_at"):
            node("timing", 6, "Lucky-day timing", decision["send_at"].replace("T", " "), decision.get("timing_reason") or "")
            edge("lucky", "timing", "day root in lucky numbers", 1.2)
            edge("f_upcoming_event", "timing", "send before the event")
        label = {"contact": "Send", "hold": "Hold", "human_review": "Human review", "no_action": "No message"}[decision["action"]]
        node("decision", 7, label, decision.get("message_preview") and f"{decision['offer'].replace('_', ' ')} on {decision['channel']}",
             decision["reason"], kind="Decision")
        edge("moderator", "decision", "verdict", 2)
        edge("guards", "decision", "can stop it", 1.5)
        edge("timing", "decision", "send at", 1.2)

    # Path: walk back from the decision; at the twin layer keep only the chosen candidate.
    incoming: dict[str, list[dict[str, Any]]] = {}
    for e in edges:
        incoming.setdefault(e["to"], []).append(e)
    on_path, stack = set(), ["decision"] if "decision" in nodes else []
    while stack:
        n = stack.pop()
        if n in on_path:
            continue
        on_path.add(n)
        for e in incoming.get(n, []):
            src = e["from"]
            if nodes[src]["layer"] == 4 and src != chosen_key:
                continue
            if nodes[src]["layer"] == 5 and chosen_key and not any(x["from"] == chosen_key and x["to"] == src for x in edges):
                continue
            stack.append(src)
    for n in nodes.values():
        n["path"] = n["id"] in on_path
    for e in edges:
        e["path"] = e["from"] in on_path and e["to"] in on_path

    return {"layers": LAYERS, "captions": CAPTIONS, "nodes": list(nodes.values()), "edges": edges,
            "decision": {k: decision.get(k) for k in ("action", "offer", "channel", "window", "send_at", "reason", "message_preview")} if decision else None}
