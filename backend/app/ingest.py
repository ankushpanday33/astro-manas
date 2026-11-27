"""Bring your own data: CSV, Excel (.xlsx) or JSON / NDJSON, any column names.

Headers are matched to the pack's columns by synonyms, dates written DD/MM/YYYY are normalised to ISO, and every
row is validated. The upload returns a report (rows loaded, rows skipped with the reason, columns we did not
recognise, a preview) instead of failing silently. Pack-specific rules live in `RULES` and `fix_row`.
"""
from __future__ import annotations

import csv
import io
import json
import re
from datetime import datetime
from typing import Any

from . import sample_data, store

SYNONYMS: dict[str, list[str]] = {
    "customer_id": ["customer_id", "cust_id", "customerid", "client_id", "user_id", "userid", "borrower_id", "account_id", "uid"],
    "name": ["name", "customer_name", "full_name", "user_name", "fullname"],
    "phone": ["phone", "mobile", "mobile_no", "mobile_number", "phone_number", "msisdn", "contact"],
    "preferred_language": ["preferred_language", "language", "lang"],
    "city": ["city", "town", "location"],
    "dob": ["dob", "date_of_birth", "birth_date", "birthdate"],
    "birth_time": ["birth_time", "time_of_birth", "tob"],
    "birth_place_name": ["birth_place_name", "birth_place", "place_of_birth", "pob", "birth_city"],
    "birth_latitude": ["birth_latitude", "lat", "latitude"],
    "birth_longitude": ["birth_longitude", "lon", "lng", "longitude"],
    "astro_consent_at": ["astro_consent_at", "consent_at", "consent_date", "astro_consent"],
    "loan_id": ["loan_id", "loan_no", "loan_number", "account_no"],
    "overdue_amount": ["overdue_amount", "overdue", "amount_overdue", "outstanding"],
    "days_past_due": ["days_past_due", "dpd"],
    "emi_amount": ["emi_amount", "emi", "instalment", "installment"],
    "collections_note": ["collections_note", "remark", "remarks", "agent_note"],
    "amount": ["amount", "amt", "value", "paid_amount"],
    "paid_at": ["paid_at", "payment_date", "paid_on", "txn_date", "transaction_date"],
    "sent_at": ["sent_at", "sent_on", "timestamp", "time", "datetime"],
    "channel": ["channel", "medium", "mode"],
    "status": ["status", "delivery_status", "state"],
    "reply_text": ["reply_text", "reply", "message", "text_reply"],
    "text": ["text", "message_text", "question", "query"],
    "started_at": ["started_at", "session_start", "opened_at", "login_at"],
    "minutes": ["minutes", "duration", "duration_min", "mins"],
    "renews_on": ["renews_on", "renewal_date", "expiry", "expiry_date"],
    "plan": ["plan", "plan_name", "pack", "product_name"],
    "price": ["price", "plan_price", "mrp"],
    "package_name": ["package_name", "package", "bundle_id", "app_package", "pkg"],
    "app_name": ["app_name", "app", "application", "app_title"],
    "event_name": ["event_name", "event", "event_type", "action"],
    "at": ["at", "event_time", "event_at", "created_at", "occurred_at", "asked_on", "asked_at", "purchased_at", "bought_at",
           "order_date", "purchase_date"],
    "comm_id": ["comm_id", "msg_id", "message_id"],
    "astrologer_id": ["astrologer_id", "astrologer", "expert", "expert_id"],
    "direction": ["direction", "dir", "in_out"],
    "cta": ["cta", "cta_name", "button", "button_name"],
    "app_signal_consent": ["app_signal_consent", "app_consent", "installed_apps_consent"],
    "detected_at": ["detected_at", "installed_at", "seen_at"],
}

# Columns that hold dates / datetimes: normalised to ISO so the brain can read them.
DATE_HINT = re.compile(r"(^|_)(dob|date|at|on|renews|paid|sent|started|made)($|_)")

RULES: dict[str, dict[str, list[str]]] = {
    # source -> required columns (beyond customer_id)
    "customers": {"required": ["dob"]},
    "loans": {"required": ["overdue_amount"]},
    "payments": {"required": ["amount", "paid_at"]},
    "promises": {"required": ["promised_date"]},
    "communications": {"required": ["channel", "sent_at"]},
    "subscriptions": {"required": ["renews_on"]},
    "usage": {"required": ["date"]},
    "sessions": {"required": ["started_at"]},
    "chats": {"required": ["at", "text"]},
    "purchases": {"required": ["at", "product"]},
    "events": {"required": ["at", "event_name"]},
    "installed_apps": {"required": []},
}

DESCRIPTIONS = {
    "customers": "One row per person. The id ties every other file together.",
    "loans": "One row per loan: what is owed, how late, and the collector's note.",
    "payments": "Every payment received, with date and method.",
    "promises": "Promises to pay, with the promised date and whether they were kept.",
    "communications": "Every message or call sent (direction out) and every reply (direction in).",
    "subscriptions": "One row per subscription period, with the renewal date.",
    "usage": "Daily usage: minutes and what they watched or listened to.",
    "sessions": "App sessions: when, how long, which screen.",
    "chats": "What users asked astrologers, in their own words.",
    "purchases": "Every purchase: consult, puja, report.",
    "events": "In-app events: viewed_login, interacted_login, completed_login, viewed_screen, clicked_cta, viewed_paywall, started_checkout, abandoned_checkout, completed_purchase.",
    "installed_apps": "Apps detected on the phone (package name and/or app name). Only tracked apps are kept; affair-dating and period / pregnancy apps are dropped at upload; community matrimony apps count only as matrimony.",
}


def _canon(key: str) -> str:
    k = re.sub(r"[^a-z0-9]+", "_", (key or "").strip().lower()).strip("_")
    for canon, alts in SYNONYMS.items():
        if k in alts:
            return canon
    return k


def _norm_date(v: Any) -> Any:
    if v is None or v == "":
        return v
    if isinstance(v, datetime):
        return v.isoformat(timespec="seconds") if (v.hour or v.minute or v.second) else v.date().isoformat()
    if hasattr(v, "isoformat"):
        return v.isoformat()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            d = datetime.strptime(s[:19], fmt)
            return s if fmt == "%Y-%m-%d" else d.isoformat(timespec="seconds")
        except ValueError:
            pass
    for fmt, has_time in (("%d/%m/%Y", False), ("%d-%m-%Y", False), ("%d.%m.%Y", False), ("%d/%m/%Y %H:%M", True),
                          ("%d/%m/%Y %H:%M:%S", True), ("%d-%m-%Y %H:%M", True), ("%d/%m/%Y %I:%M %p", True),
                          ("%d/%m/%Y %I:%M%p", True), ("%d-%m-%Y %I:%M %p", True), ("%Y-%m-%d %I:%M %p", True)):
        try:
            d = datetime.strptime(s, fmt)
            return d.isoformat(timespec="seconds") if has_time else d.date().isoformat()
        except ValueError:
            pass
    return s


NUMERIC = {"amount", "price", "minutes", "overdue_amount", "emi_amount", "days_past_due", "birth_latitude", "birth_longitude"}
CHANNELS = {"whatsapp": "whatsapp", "wa": "whatsapp", "push": "push", "push_notification": "push", "notification": "push",
            "in_app": "in_app", "inapp": "in_app", "in-app": "in_app", "app": "in_app", "sms": "sms", "text": "sms",
            "voice": "voice", "call": "voice", "ivr": "voice", "email": "email", "mail": "email"}
STATUS = {"seen": "read", "opened": "read", "read": "read", "delivered": "delivered", "sent": "delivered", "failed": "failed",
          "undelivered": "failed", "bounced": "failed", "answered": "answered", "received": "received"}


def parse_time(v: Any) -> str | None:
    """'10:35', '6:20 PM', '06:20pm', '18.45', '06:20:00' -> 'HH:MM'. Anything else -> None."""
    if v in (None, ""):
        return None
    if hasattr(v, "strftime"):
        return v.strftime("%H:%M")
    t = str(v).strip().upper().replace(".", ":")
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p"):
        try:
            return datetime.strptime(t, fmt).strftime("%H:%M")
        except ValueError:
            pass
    return None


def _num(v: Any) -> Any:
    if v in (None, "") or isinstance(v, (int, float)):
        return v
    t = re.sub(r"[₹,\s]|rs\.?|inr", "", str(v), flags=re.I)
    try:
        return float(t)
    except ValueError:
        return None


def read_file(filename: str, raw: bytes) -> list[dict[str, Any]]:
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm")):
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        ws = wb.worksheets[0]
        it = ws.iter_rows(values_only=True)
        header = [str(h) if h is not None else "" for h in next(it, [])]
        return [dict(zip(header, row)) for row in it if any(c not in (None, "") for c in row)]
    text = raw.decode("utf-8-sig")
    if name.endswith(".json"):
        data = json.loads(text)
        return data if isinstance(data, list) else data.get("rows", [])
    if name.endswith((".ndjson", ".jsonl")):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    return list(csv.DictReader(io.StringIO(text), dialect=dialect))


def known_columns(source: str, pack_id: str) -> list[str]:
    gen = sample_data.DATASETS.get(pack_id)
    if not gen:
        return []
    rows = gen(n=12).get(source, [])
    cols: list[str] = []
    for r in rows:
        for k in r:
            if not k.startswith("_") and k not in cols:
                cols.append(k)
    return cols


# Birth places the demo can geocode without an external service (lat, lon). Production uses a geocoder.
CITIES = {
    "delhi": (28.6139, 77.2090), "new delhi": (28.6139, 77.2090), "mumbai": (19.0760, 72.8777), "kolkata": (22.5726, 88.3639),
    "chennai": (13.0827, 80.2707), "bengaluru": (12.9716, 77.5946), "bangalore": (12.9716, 77.5946), "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567), "ahmedabad": (23.0225, 72.5714), "jaipur": (26.9124, 75.7873), "lucknow": (26.8467, 80.9462),
    "kanpur": (26.4499, 80.3319), "nagpur": (21.1458, 79.0882), "indore": (22.7196, 75.8577), "bhopal": (23.2599, 77.4126),
    "patna": (25.5941, 85.1376), "varanasi": (25.3176, 82.9739), "surat": (21.1702, 72.8311), "vadodara": (22.3072, 73.1812),
    "chandigarh": (30.7333, 76.7794), "amritsar": (31.6340, 74.8723), "ludhiana": (30.9010, 75.8573), "kochi": (9.9312, 76.2673),
    "thiruvananthapuram": (8.5241, 76.9366), "coimbatore": (11.0168, 76.9558), "madurai": (9.9252, 78.1198), "guwahati": (26.1445, 91.7362),
    "bhubaneswar": (20.2961, 85.8245), "ranchi": (23.3441, 85.3096), "dehradun": (30.3165, 78.0322), "agra": (27.1767, 78.0081),
    "prayagraj": (25.4358, 81.8463), "allahabad": (25.4358, 81.8463), "visakhapatnam": (17.6868, 83.2185), "mysuru": (12.2958, 76.6394),
    "noida": (28.5355, 77.3910), "gurugram": (28.4595, 77.0266), "gurgaon": (28.4595, 77.0266), "raipur": (21.2514, 81.6296),
}
YES = {"yes", "y", "true", "1", "consented", "agree", "agreed"}


def fix_row(source: str, r: dict[str, Any]) -> str | None:
    """Astro rules: people need a real date of birth and explicit consent; app rows are minimised at the door."""
    if source == "installed_apps":
        from .astro import app_catalog

        if not (r.get("package_name") or r.get("app_name")):
            return "needs package_name or app_name"
        kept, reason = app_catalog.scrub_row(r)
        if not kept:
            return reason
        r.clear()
        r.update(kept)
        return None
    if source == "events":
        if not r.get("at") and r.get("sent_at"):
            r["at"] = r.pop("sent_at")
        r["event_name"] = str(r.get("event_name") or "").strip().lower().replace(" ", "_")
        return None
    if source != "customers":
        return None
    from datetime import date as _date

    try:
        dob = _date.fromisoformat(str(r.get("dob"))[:10])
    except ValueError:
        return f"dob '{r.get('dob')}' is not a date (use DD/MM/YYYY)"
    if not 1900 <= dob.year <= _date.today().year:
        return f"dob year {dob.year} looks wrong"
    consent = str(r.get("astro_consent_at") or "").strip()
    if consent.lower() in YES:
        r["astro_consent_at"] = _date.today().isoformat()  # consent recorded at upload time
    elif consent.lower() in {"", "no", "n", "false", "0"}:
        r["astro_consent_at"] = None  # numerology and Panchang will NOT be computed (PRD 5.8)
    raw_time = r.get("birth_time")
    r["birth_time"] = parse_time(raw_time)
    if raw_time not in (None, "") and r["birth_time"] is None:
        r["birth_time_note"] = f"birth time '{raw_time}' not understood: Panchang skipped, numerology still computed"
    conf = str(r.get("birth_time_confidence") or "").upper()
    r["birth_time_confidence"] = "UNKNOWN" if not r.get("birth_time") else conf if conf in {"EXACT", "APPROXIMATE"} else "EXACT"
    if r.get("birth_latitude") in (None, "") and r.get("birth_place_name"):
        key = str(r["birth_place_name"]).split(",")[0].strip().lower()
        if key in CITIES:
            r["birth_latitude"], r["birth_longitude"] = CITIES[key]
    if not r.get("birth_timezone"):
        r["birth_timezone"] = "Asia/Kolkata"
    app_consent = str(r.get("app_signal_consent") or "").strip()
    if app_consent.lower() in YES:
        r["app_signal_consent"] = _date.today().isoformat()
    elif app_consent.lower() in {"", "no", "n", "false", "0"}:
        r["app_signal_consent"] = None  # installed apps will be ignored for this user
    if not r.get("numerology_name") and r.get("name"):
        r["numerology_name"] = str(r["name"]).split()[0].upper()
    return None


def ingest(source: str, filename: str, raw: bytes, pack_id: str, mode: str = "append") -> dict[str, Any]:
    if source not in sample_data.ID_FIELDS:
        raise ValueError(f"source must be one of {sorted(sample_data.ID_FIELDS)}")
    rows_in = read_file(filename, raw)
    if not rows_in:
        raise ValueError("The file has no rows.")
    id_field = sample_data.ID_FIELDS[source]
    known = set(known_columns(source, pack_id)) | {id_field, "customer_id"}
    original = list(rows_in[0].keys())
    mapping = {h: _canon(h) for h in original}
    unknown = sorted({c for c in mapping.values() if c not in known})
    required = ["customer_id"] + RULES.get(source, {}).get("required", [])
    missing_cols = [c for c in required if c not in mapping.values()]
    if "customer_id" in missing_cols:
        raise ValueError(f"No customer id column found. Rename one of your columns to customer_id (seen: {', '.join(original)}).")

    good, skipped, fixes = [], [], {}
    known_ids = set(store.customer_ids()) if source != "customers" else set()
    by_lower = {k.lower(): k for k in known_ids}
    for i, raw_row in enumerate(rows_in, start=2):
        r = {mapping.get(k, _canon(k)): (v.strip() if isinstance(v, str) else v) for k, v in raw_row.items() if k is not None}
        for k in list(r):
            if DATE_HINT.search(k) or k in {"birth_time"}:
                r[k] = _norm_date(r[k]) if k != "birth_time" else (str(r[k])[:5] if r[k] not in (None, "") else None)
        if r.get("customer_id") in (None, ""):
            skipped.append({"row": i, "reason": "customer_id is empty"})
            continue
        r["customer_id"] = str(r["customer_id"]).strip()
        if known_ids and r["customer_id"] not in known_ids and r["customer_id"].lower() in by_lower:
            fixes[f"{r['customer_id']} -> {by_lower[r['customer_id'].lower()]}"] = fixes.get(f"{r['customer_id']} -> {by_lower[r['customer_id'].lower()]}", 0) + 1
            r["customer_id"] = by_lower[r["customer_id"].lower()]
        for k in NUMERIC & set(r):
            r[k] = _num(r[k])
        if source == "communications":
            if r.get("channel"):
                key = str(r["channel"]).strip().lower().replace(" ", "_")
                r["channel"] = CHANNELS.get(key, CHANNELS.get(key.split("_")[0], key))
            if r.get("status"):
                r["status"] = STATUS.get(str(r["status"]).strip().lower(), str(r["status"]).strip().lower())
            r["direction"] = str(r.get("direction") or "out").strip().lower()
        empty = [c for c in required if c != "customer_id" and r.get(c) in (None, "")]
        if empty:
            skipped.append({"row": i, "reason": f"missing {', '.join(empty)}"})
            continue
        reason = fix_row(source, r)
        if reason:
            skipped.append({"row": i, "reason": reason})
            continue
        r.setdefault(id_field, f"{source[:3].upper()}-{r['customer_id']}-{i}")
        good.append(r)

    from collections import Counter

    dup = Counter(r[id_field] for r in good if source == "customers")
    duplicates = sorted(k for k, n in dup.items() if n > 1)
    orphans = Counter(r["customer_id"] for r in good if known_ids and r["customer_id"] not in known_ids)
    if mode == "replace":
        with store.db() as conn:
            conn.execute("DELETE FROM records WHERE source=?", (source,))
    loaded = store.put_records(source, good, id_field, "customer_id") if good else 0
    return {
        "source": source, "file": filename, "mode": mode, "rows_in_file": len(rows_in), "loaded": loaded,
        "skipped": len(skipped), "skipped_rows": skipped[:50],
        "column_mapping": {k: v for k, v in mapping.items() if k != v}, "unrecognised_columns": unknown,
        "missing_required_columns": [c for c in missing_cols if c != "customer_id"],
        "preview": good[:3], "next": "Build brains and decide to see these rows in every brain.",
        "duplicate_ids": duplicates, "orphan_rows": sum(orphans.values()), "orphan_ids": sorted(orphans)[:20],
        "fixes": ({"ids_matched_ignoring_case": sum(fixes.values()), "examples": list(fixes)[:5]} if fixes else {}),
    }


def schema(pack_id: str, sources: list[str]) -> list[dict[str, Any]]:
    out = []
    for s in sources:
        cols = known_columns(s, pack_id)
        req = ["customer_id"] + RULES.get(s, {}).get("required", [])
        out.append({"source": s, "description": DESCRIPTIONS.get(s, ""), "id_field": sample_data.ID_FIELDS[s],
                    "required": req, "columns": cols, "rows_now": store.source_counts().get(s, 0)})
    return out


def template_csv(source: str, pack_id: str) -> str:
    rows = sample_data.DATASETS[pack_id](n=6).get(source, [])[:5]
    cols = known_columns(source, pack_id)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: v for k, v in r.items() if not k.startswith("_")})
    return buf.getvalue()
