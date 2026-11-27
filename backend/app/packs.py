"""Goal pack for the AI astrology app: next best action per user, grounded in their stored astro row and behaviour."""
from __future__ import annotations

from typing import Any

PACKS: dict[str, dict[str, Any]] = {
    "astro_engagement": {
        "id": "astro_engagement",
        "title": "AI Astro: next best action",
        "summary": "For every user, decide what to offer (horoscope, topic reading, astrologer, puja, report), on which channel and when, from their chart and their behaviour.",
        "objects": {
            "User": {"source": "customers", "id": "customer_id",
                     "fields": ["preferred_language", "city", "consent_whatsapp", "consent_push", "astro_consent_at", "app_signal_consent", "birth_time_confidence"]},
            "AstroRow": {"source": "user", "id": "id", "fields": ["radical_number", "destiny_number", "nakshatra_name", "lucky_numbers"]},
            "Session": {"source": "sessions", "id": "session_id", "fields": ["started_at", "minutes", "screen", "content_tag"]},
            "Chat": {"source": "chats", "id": "chat_id", "fields": ["at", "astrologer_id", "text", "minutes"]},
            "Purchase": {"source": "purchases", "id": "purchase_id", "fields": ["at", "product", "amount"]},
            "Communication": {"source": "communications", "id": "comm_id", "fields": ["channel", "sent_at", "status", "direction", "offer"]},
            "Event": {"source": "events", "id": "event_id", "fields": ["at", "event_name", "screen", "cta"]},
            "InstalledApp": {"source": "installed_apps", "id": "install_id", "fields": ["category", "use", "detected_at"]},
        },
        "links": [
            {"from": "AstroRow", "type": "computed_for", "to": "User", "on": "user.id"},
            {"from": "Session", "type": "used_by", "to": "User", "on": "sessions.customer_id"},
            {"from": "Chat", "type": "asked_by", "to": "User", "on": "chats.customer_id"},
            {"from": "Purchase", "type": "bought_by", "to": "User", "on": "purchases.customer_id"},
            {"from": "Communication", "type": "sent_to", "to": "User", "on": "communications.customer_id"},
            {"from": "Event", "type": "did", "to": "User", "on": "events.customer_id"},
            {"from": "InstalledApp", "type": "installed_by", "to": "User", "on": "installed_apps.customer_id"},
        ],
        "text_columns": ["chats.text (dated by at)", "communications.reply_text (dated by sent_at)"],
        "beliefs": ["engagement", "purchase_intent", "topic_focus", "anxiety", "reachability", "purchase_propensity", "money_pressure"],
        "conversion": "a deep session (5+ minutes) or a purchase within 3 days of the message",
        "channels": ["push", "whatsapp", "in_app"],
        "windows": {"morning": (7, 12), "afternoon": (12, 17), "evening": (17, 21)},
        "quiet_hours_note": "No messages outside 07:00 to 21:00; no fear-based copy; no gemstone prescriptions",
        # Offers play the role of 'tones' in the twin: what we put in front of the user.
        "tones": ["daily_horoscope", "topic_reading", "astrologer_consult", "planet_puja", "personality_report", "name_correction", "resume_checkout"],
        "frequency_cap": {"per_day": 1, "per_week": 4},
        "templates": {
            "daily_horoscope": "{name}, today's guidance for {nakshatra} Nakshatra is ready. A calm look at your day: {link}",
            "topic_reading": "{name}, a {topic} reading based on your chart ({planet} as your ruling planet) is ready for you: {link}",
            "astrologer_consult": "{name}, {astrologer} specialises in {planet} charts like yours. First 5 minutes free: {link}",
            "planet_puja": "{name}, a {planet_name} puja is traditionally associated with your Radical number {radical}. Book with a temple partner: {link}",
            "personality_report": "{name}, your Birth Panchang personality: {title}. Five dimensions, with the proof: {link}",
            "name_correction": "{name}, curious how a spelling changes your Name number ({name_number} today)? Compare spellings side by side: {link}",
            "resume_checkout": "{name}, you left {checkout_item} halfway. It is saved for you whenever you are ready, no rush: {link}",
        },
    },
}

# Fictional astrologer roster for matching on nakshatra_lord / radical_planet (PRD 5.7).
ASTROLOGERS = [
    {"id": "AS-01", "name": "Acharya Vivek", "planets": ["SATURN", "RAHU", "KETU"], "topics": ["career", "finance"]},
    {"id": "AS-02", "name": "Pandita Meera", "planets": ["MOON", "VENUS"], "topics": ["marriage", "relationships"]},
    {"id": "AS-03", "name": "Guru Raghav", "planets": ["JUPITER", "SUN"], "topics": ["education", "career"]},
    {"id": "AS-04", "name": "Jyotishi Ananya", "planets": ["MERCURY", "MARS"], "topics": ["health", "finance"]},
]


def get_pack(pack_id: str) -> dict[str, Any]:
    if pack_id not in PACKS:
        raise KeyError(f"Unknown pack: {pack_id}")
    return PACKS[pack_id]


def pack_summaries() -> list[dict[str, Any]]:
    return [
        {"id": p["id"], "title": p["title"], "summary": p["summary"], "objects": list(p["objects"].keys()),
         "links": p["links"], "beliefs": p["beliefs"], "conversion": p["conversion"], "channels": p["channels"],
         "text_columns": p["text_columns"], "quiet_hours_note": p["quiet_hours_note"]}
        for p in PACKS.values()
    ]
