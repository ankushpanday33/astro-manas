"""Facts: answers computed in code, never guessed by a model. Each one cites the rows it read and the formula."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Callable


def _d(value: Any) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value)[:19]).date() if "T" in str(value) else date.fromisoformat(str(value)[:10])


def _dt(value: Any) -> datetime | None:
    return datetime.fromisoformat(str(value)[:19]) if value else None


def _truthy(v: Any) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def _f(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def window_of(hour: int, windows: dict[str, tuple[int, int]]) -> str | None:
    for name, (start, end) in windows.items():
        if start <= hour < end:
            return name
    return None


def comm_stats(records: dict[str, list[dict]], windows: dict[str, tuple[int, int]], success_dates: list[date]) -> dict[str, Any]:
    """Per channel x window: sends, delivered, read, replied, converted_3d (a conversion within 3 days of the send).

    Sends outside the pack's windows are still counted under 'outside' so nothing is silently dropped.
    """
    comms = sorted(records.get("communications", []), key=lambda c: c.get("sent_at", ""))
    inbound = [c for c in comms if c.get("direction") == "in"]
    stats: dict[str, dict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(lambda: {
        "sends": 0, "delivered": 0, "read": 0, "replied": 0, "converted_3d": 0, "rows": []}))
    for c in comms:
        if c.get("direction") != "out":
            continue
        sent = _dt(c.get("sent_at"))
        if not sent:
            continue
        ch = c.get("channel", "unknown")
        w = window_of(sent.hour, windows) or "outside"
        cell = stats[ch][w]
        cell["sends"] += 1
        cell["rows"].append(c["_row_id"])
        status = str(c.get("status", "")).lower()
        if status in {"delivered", "read", "answered"}:
            cell["delivered"] += 1
        if status in {"read", "answered"}:
            cell["read"] += 1
        if any(i.get("channel") == ch and sent < (_dt(i.get("sent_at")) or sent) <= sent + timedelta(hours=48) for i in inbound):
            cell["replied"] += 1
        # Only a message that was actually read (or a call answered) gets credit for a conversion that followed it.
        if status in {"read", "answered"} and any(sent.date() <= s <= sent.date() + timedelta(days=3) for s in success_dates):
            cell["converted_3d"] += 1
    return {ch: dict(ws) for ch, ws in stats.items()}


class FactBook:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, fid: str, question: str, value: Any, formula: str, cites: list[tuple[str, str]], unit: str | None = None) -> None:
        self.items.append({
            "id": fid, "question": question, "value": value, "unit": unit, "formula": formula,
            "citations": [{"source": s, "row_id": r} for s, r in cites], "kind": "computed",
        })


def _channel_rates(fb: FactBook, stats: dict[str, Any], channels: list[str]) -> None:
    for ch in channels:
        cells = stats.get(ch, {})
        sends = sum(c["sends"] for c in cells.values())
        rows = [(f"communications", r) for c in cells.values() for r in c["rows"]][:25]
        if ch == "voice":
            ans = sum(c["read"] for c in cells.values())
            fb.add(f"{ch}_answer_rate", "How often do they pick up calls?", round(ans / sends, 2) if sends else None,
                   f"answered / calls placed = {ans}/{sends}", rows)
        else:
            rd = sum(c["read"] for c in cells.values())
            rp = sum(c["replied"] for c in cells.values())
            fb.add(f"{ch}_read_rate", f"How often do they read {ch} messages?", round(rd / sends, 2) if sends else None,
                   f"read / sent = {rd}/{sends}", rows)
            fb.add(f"{ch}_reply_rate", f"How often do they reply on {ch}?", round(rp / sends, 2) if sends else None,
                   f"replies within 48h / sent = {rp}/{sends}", rows)


def _common_comm_facts(fb: FactBook, records: dict[str, list[dict]], stats: dict[str, Any], today: date) -> None:
    comms = records.get("communications", [])
    out90 = [c for c in comms if c.get("direction") == "out" and (_d(c.get("sent_at")) or today) >= today - timedelta(days=90)]
    fb.add("outbound_contacts_90d", "How many times did we contact them in 90 days?", len(out90),
           "count(communications where direction=out and sent_at >= today-90d)", [("communications", c["_row_id"]) for c in out90][:25])
    last7 = [c for c in comms if c.get("direction") == "out" and (_d(c.get("sent_at")) or date.min) >= today - timedelta(days=7)]
    fb.add("contacts_last_7d", "How many contacts in the last 7 days?", len(last7),
           "count(outbound in last 7 days)", [("communications", c["_row_id"]) for c in last7])
    inbound = sorted((c for c in comms if c.get("direction") == "in"), key=lambda c: c.get("sent_at", ""))
    if inbound:
        last = inbound[-1]
        fb.add("days_since_last_reply", "When did they last reply to us?", (today - _d(last["sent_at"])).days,
               f"today - last inbound sent_at ({last['sent_at'][:10]}) on {last.get('channel')}", [("communications", last["_row_id"])], "days")
    else:
        fb.add("days_since_last_reply", "When did they last reply to us?", None, "no inbound message on record", [], "days")

    best, best_rate, best_rows, best_n = None, -1.0, [], 0
    for ch, cells in stats.items():
        for w, c in cells.items():
            if c["sends"] >= 3 and w != "outside":
                rate = (c["read"] + 2 * c["replied"]) / (3 * c["sends"])
                if rate > best_rate:
                    best, best_rate, best_rows, best_n = f"{ch} · {w}", rate, c["rows"], c["sends"]
    fb.add("best_responding_slot", "Where and when do they actually respond?", best,
           f"argmax over channel x window of (reads + 2*replies)/(3*sends), min 3 sends; chosen slot had {best_n} sends" if best else "fewer than 3 sends in every slot",
           [("communications", r) for r in best_rows][:25])


def astro_facts(records: dict[str, list[dict]], pack: dict[str, Any], today: date, memory: list[dict],
                row: dict[str, Any] | None) -> tuple[list[dict], dict]:
    """Chart facts read from the stored "user" row (never recomputed here) plus behaviour facts from app data."""
    fb = FactBook()
    uid = (records.get("customers") or [{}])[0].get("customer_id", "")
    rc = lambda *cols: [("user", f"{uid}.{c}") for c in cols]

    fb.add("astro_consent", "Did they consent to birth-data use?", bool(row), "user.astro_consent_at is set" if row else "no consent: chart not computed (PRD 5.8)",
           rc("astro_consent_at") if row else [])
    if row:
        fb.add("radical_number", "Radical number (Mulank)?", f"{row['radical_number']} · {row['radical_planet']}", row["radical_calculation"], rc("radical_number", "radical_calculation"))
        fb.add("destiny_number", "Destiny number (Bhagyank)?", f"{row['destiny_number']} · {row['destiny_planet']}", row["destiny_calculation"], rc("destiny_number", "destiny_calculation"))
        fb.add("name_number", "Name number (Namank)?", f"{row['name_number']} · {row['name_planet']}", row["name_calculation"], rc("name_number", "name_calculation"))
        fb.add("lucky_numbers", "Lucky numbers?", row["lucky_numbers"], "top tier of weighted planetary-friendship scores (2/2/1)", rc("number_scores", "lucky_numbers"))
        fb.add("ruling_planet", "Which planet leads their chart?", row["radical_planet"], "planet of the Radical number (PRD 3.6)", rc("radical_planet"))
        fb.add("nakshatra", "Janma Nakshatra?", f"{row['nakshatra_name']} pada {row['nakshatra_pada']} · {row['nakshatra_lord']}" if row.get("nakshatra_name") else None,
               "floor(moon_long / 13°20') + 1 at the exact birth instant" if row.get("nakshatra_name") else "Panchang not computed: birth time unknown",
               rc("nakshatra_index", "nakshatra_pada", "moon_longitude") if row.get("nakshatra_name") else [])
        fb.add("nakshatra_lord", "Lord of the Nakshatra?", row.get("nakshatra_lord"), "VIMSHOTTARI[(index - 1) % 9]", rc("nakshatra_lord") if row.get("nakshatra_lord") else [])
        fb.add("personality_title", "Birth Panchang personality title?", row.get("personality_title"), f"group H, written by {row.get('ai_model')}", rc("personality_title"))
        fb.add("birth_time_confidence", "How sure is the birth time?", row["birth_time_confidence"],
               f"uncertain angas: {', '.join(row.get('panchang_uncertain_angas') or []) or 'none'}", rc("birth_time_confidence", "panchang_uncertain_angas"))

    sessions = sorted(records.get("sessions", []), key=lambda s: s.get("started_at", ""))
    sc = lambda rows: [("sessions", s["_row_id"]) for s in rows][:25]
    s7 = [s for s in sessions if (_d(s["started_at"]) or date.min) >= today - timedelta(days=7)]
    s30 = [s for s in sessions if (_d(s["started_at"]) or date.min) >= today - timedelta(days=30)]
    prev = [s for s in sessions if today - timedelta(days=60) <= (_d(s["started_at"]) or date.min) < today - timedelta(days=30)]
    fb.add("sessions_7d", "How often did they open the app this week?", len(s7), "count(sessions, last 7 days)", sc(s7))
    trend = round((len(s30) - len(prev)) / len(prev), 2) if prev else None
    fb.add("usage_trend", "Is usage rising or falling?", trend, f"(last 30d - previous 30d) / previous 30d = ({len(s30)}-{len(prev)})/{len(prev) or 1}", sc(s30 + prev))
    deep = [s for s in s30 if _f(s.get("minutes")) >= 5]
    fb.add("deep_sessions_30d", "How many deep (5+ min) sessions in 30 days?", len(deep), "count(sessions with minutes >= 5, last 30d)", sc(deep))
    fb.add("days_since_last_session", "When did they last open the app?", (today - _d(sessions[-1]["started_at"])).days if sessions else None,
           "today - max(sessions.started_at)", sc(sessions[-1:]), "days")
    hours = Counter(window_of(_dt(s["started_at"]).hour, pack["windows"]) or "outside" for s in sessions)
    slot = hours.most_common(1)[0][0] if hours else None
    fb.add("active_window", "When of day are they usually in the app?", slot, "mode(window of session start hour)", sc(sessions))
    tag = Counter(s.get("content_tag") for s in s30).most_common(1)
    fb.add("top_content", "What do they read most?", tag[0][0] if tag else None, "mode(sessions.content_tag, last 30d)", sc(s30))

    chats = records.get("chats", [])
    fb.add("chats_60d", "How many astrologer chats in 60 days?", len(chats), "count(chats)", [("chats", c["_row_id"]) for c in chats])
    pur = sorted(records.get("purchases", []), key=lambda p: p.get("at", ""))
    p90 = [p for p in pur if (_d(p["at"]) or date.min) >= today - timedelta(days=90)]
    fb.add("purchases_90d", "How many purchases in 90 days?", len(p90), "count(purchases, last 90d)", [("purchases", p["_row_id"]) for p in p90])
    fb.add("spend_90d", "How much did they spend in 90 days?", round(sum(_f(p.get("amount")) for p in p90)), "sum(purchases.amount, last 90d)",
           [("purchases", p["_row_id"]) for p in p90], "INR")
    fb.add("favourite_product", "What do they buy?", Counter(p["product"] for p in pur).most_common(1)[0][0] if pur else None, "mode(purchases.product)",
           [("purchases", p["_row_id"]) for p in pur])

    topics = Counter(m["detail"] for m in memory if m["kind"] == "topic")
    t_rows = [m["ref"] for m in memory if m["kind"] == "topic"]
    fb.items.append({"id": "main_topic", "question": "What is on their mind?", "value": topics.most_common(1)[0][0] if topics else None, "unit": None,
                     "formula": f"most frequent topic read from chats ({sum(topics.values())} mentions)" if topics else "no topic in any chat",
                     "citations": t_rows[:25], "kind": "extracted"})

    def latest(kind: str) -> dict | None:
        found = [m for m in memory if m["kind"] == kind]
        return found[-1] if found else None

    for kind, fid, q in [("anxiety", "anxiety_flag", "Do they sound anxious?"), ("contact_objection", "contact_objection_flag", "Did they ask us to stop messaging?")]:
        m = latest(kind)
        fb.items.append({"id": fid, "question": q, "value": bool(m), "unit": None,
                         "formula": f"read from text ({m['method']}), written {m['written_on']}" if m else "no such signal",
                         "citations": [m["ref"]] if m else [], "kind": "extracted"})
    ev = latest("upcoming_event")
    ev_date = date.fromisoformat(ev["resolved_date"]) if ev and ev.get("resolved_date") else None
    if ev and ev_date and ev_date < today:
        value, formula = None, f"{ev['detail']} on {ev_date.strftime('%d/%m/%Y')} has already passed (written {ev['written_on']})"
    elif ev:
        value = f"{ev['detail']} on {ev_date.strftime('%d/%m/%Y')}" if ev_date else ev["detail"]
        formula = f"read from text written {ev['written_on']}; date resolved against that day"
    else:
        value, formula = None, "none mentioned"
    fb.items.append({"id": "upcoming_event", "question": "Is something important coming up?", "value": value, "unit": None,
                     "formula": formula, "citations": [ev["ref"]] if ev else [], "kind": "extracted"})
    tp = latest("time_preference")
    fb.items.append({"id": "stated_time_preference", "question": "Did they say when to contact them?", "value": tp["detail"] if tp else None, "unit": None,
                     "formula": f"read from text, written {tp['written_on']}" if tp else "not stated", "citations": [tp["ref"]] if tp else [], "kind": "extracted"})

    # Installed-app signals (only with app_signal_consent; rows were already minimised at upload).
    from ..astro import app_catalog
    from .. import predict

    profile = (records.get("customers") or [{}])[0]
    consent = bool(profile.get("app_signal_consent"))
    apps = records.get("installed_apps", []) if consent else []
    by_use: dict[str, list[str]] = {"personalise": [], "protect": []}
    rows_by_cat: dict[str, list[tuple[str, str]]] = {}
    for a in apps:
        cat = a.get("category")
        if cat in app_catalog.CATEGORIES and a.get("use") in by_use:
            if cat not in by_use[a["use"]]:
                by_use[a["use"]].append(cat)
            rows_by_cat.setdefault(cat, []).append(("installed_apps", a["_row_id"]))
    fb.add("app_signal_consent", "May we use installed-app signals?", consent,
           "user.app_signal_consent is set" if consent else "no app-signal consent: installed apps are ignored", [])
    if consent:
        lab = lambda cats: [app_catalog.CATEGORIES[c]["label"] for c in cats]
        fb.add("app_interests", "What do their apps say they care about?", lab(by_use["personalise"]) or None,
               "tracked app categories with use = personalise", [r for c in by_use["personalise"] for r in rows_by_cat[c]][:25])
        topic = next((app_catalog.CATEGORIES[c]["topic"] for c in ("matrimony", "jobs", "education", "dating", "investing", "mainstream_credit")
                      if c in by_use["personalise"] and app_catalog.CATEGORIES[c].get("topic")), None)
        fb.add("app_topic_hint", "Which life topic do their apps point to?", topic,
               "first of matrimony, jobs, education, dating, investing present on the phone", [r for c in by_use["personalise"] for r in rows_by_cat[c]][:10])
        fb.add("money_pressure_flag", "Any sign of short-term money pressure?", "high_interest_loan" in by_use["protect"],
               "an instant / high-interest loan app is installed (protect only: switches off paid offers)", rows_by_cat.get("high_interest_loan", []))
        fb.add("gaming_exposure_flag", "Any real-money gaming exposure?", "betting" in by_use["protect"],
               "a betting / fantasy / rummy app is installed (protect only: no lucky-number-for-betting, no paid push)", rows_by_cat.get("betting", []))
        fb.add("competitor_astro_user", "Do they use other astrology apps?", "astro_competitor" in by_use["personalise"],
               "a competitor astrology app is installed", rows_by_cat.get("astro_competitor", []))
        fb.add("premium_affinity", "Do they prefer premium, private service?", "premium_dating" in by_use["personalise"],
               "member of an invitation-only community app", rows_by_cat.get("premium_dating", []))
        fb.add("pays_by_upi", "Can they pay by UPI?", "payments_upi" in by_use["personalise"], "a UPI / wallet app is installed",
               rows_by_cat.get("payments_upi", []))

    # In-app events and the predictions built on them.
    pred = predict.predict(records.get("events", []), by_use, len(p90), today)
    feats = pred["features"]
    ev_rows = [("events", r) for r in pred["rows"]]
    fb.add("events_30d", "How many in-app events in 30 days?", feats["events_30d"], "count(events, last 30 days)", ev_rows)
    fb.add("cta_clicks_7d", "How many CTA clicks this week?", feats["cta_clicks_7d"], "count(event_name = clicked_cta, last 7 days)", ev_rows)
    fb.add("top_cta", "Which CTA do they click most?", feats["top_cta"], "mode(cta where event_name = clicked_cta, 30d)", ev_rows)
    fb.add("abandoned_checkout", "Did they leave a checkout halfway?", feats["abandoned_item"],
           "abandoned_checkout in 14 days with no later completed_purchase for the same item", ev_rows)
    fb.add("login_dropoff", "Did they start login and not finish?", bool(feats["login_dropoff"]),
           f"viewed_login {feats['login_attempts_30d']} times, completed {feats['login_completed']} (30d)", ev_rows)
    for key, q in (("purchase_propensity_7d", "How likely are they to buy in the next 7 days?"),
                   ("churn_risk_14d", "How likely are they to go quiet for 14 days?")):
        pr = pred[key]
        fb.add(key, q, pr["value"], ("logistic over named event features; top drivers: " + ", ".join(f"{d['feature']} {d['effect']:+}" for d in pr["drivers"][:3]))
               if pr["status"] == "ok" else pr["note"], ev_rows)

    success = [_d(s["started_at"]) for s in sessions if _f(s.get("minutes")) >= 5] + [_d(p["at"]) for p in pur]
    stats = comm_stats(records, pack["windows"], [d for d in success if d])
    _channel_rates(fb, stats, pack["channels"])
    _common_comm_facts(fb, records, stats, today)
    return fb.items, stats, {**pred, "app_signals": by_use if consent else None, "app_consent": consent}


