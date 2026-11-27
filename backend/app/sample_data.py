"""Synthetic demo users for the AI astrology app. Every person here is fictional."""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from typing import Any

FIRST = ["Aarav", "Priya", "Rohit", "Sneha", "Vikram", "Anjali", "Karan", "Pooja", "Arjun", "Neha", "Rahul", "Kavya",
         "Suresh", "Meena", "Imran", "Ravi", "Lakshmi", "Deepak", "Sunita", "Manoj", "Asha", "Nikhil", "Divya", "Sanjay",
         "Rekha", "Amit", "Geeta", "Harsh", "Nisha", "Tarun", "Swati", "Gaurav", "Ritu", "Ajay", "Bhavna", "Isha"]
LAST = ["Sharma", "Verma", "Patel", "Iyer", "Reddy", "Singh", "Das", "Nair", "Joshi", "Gupta", "Mehta", "Kulkarni",
        "Banerjee", "Pillai", "Yadav", "Rao", "Mishra", "Chauhan"]
PLACES = [("Lucknow, IN", 26.8467, 80.9462, "Hindi"), ("Varanasi, IN", 25.3176, 82.9739, "Hindi"),
          ("Jaipur, IN", 26.9124, 75.7873, "Hindi"), ("Pune, IN", 18.5204, 73.8567, "Marathi"),
          ("Chennai, IN", 13.0827, 80.2707, "Tamil"), ("Kolkata, IN", 22.5726, 88.3639, "Bengali"),
          ("Hyderabad, IN", 17.3850, 78.4867, "Telugu"), ("Ahmedabad, IN", 23.0225, 72.5714, "Gujarati"),
          ("Delhi, IN", 28.6139, 77.2090, "Hindi"), ("Bengaluru, IN", 12.9716, 77.5946, "English")]

# archetype: weight, active window (hours), sessions per week, deep-session share, read probs by channel,
# chat lines, purchase products, consent, birth-time confidence
ARCH = {
    "daily_devotee": (22, (6, 9), 7, 0.7, {"push": 0.85, "in_app": 0.9, "whatsapp": 0.4},
                      ["aaj ka din kaisa rahega?", "which colour is good for me today?"], ["planet_puja"], "EXACT"),
    "career_anxious": (20, (19, 21), 3, 0.5, {"whatsapp": 0.8, "push": 0.3, "in_app": 0.5},
                       ["job interview next week, bahut tension hai", "naukri kab lagegi? worried about career",
                        "promotion milega ya nahi, pareshan hoon"], ["astrologer_consult", "topic_reading"], "EXACT"),
    "marriage_seeker": (16, (13, 16), 3, 0.6, {"in_app": 0.8, "whatsapp": 0.5, "push": 0.4},
                        ["shaadi kab hogi? rishta dekh rahe hain", "kundli matching for marriage please"],
                        ["astrologer_consult", "topic_reading"], "APPROXIMATE"),
    "curious_browser": (18, (20, 21), 2, 0.3, {"push": 0.6, "in_app": 0.6, "whatsapp": 0.2},
                        ["what does my nakshatra mean?", "mera lucky number kya hai"], ["personality_report"], "EXACT"),
    "lapsing": (14, (18, 21), 1, 0.2, {"push": 0.2, "whatsapp": 0.35, "in_app": 0.3},
                ["not opening much these days", "notifications band karo"], [], "UNKNOWN"),
    "no_consent": (10, (10, 12), 2, 0.3, {"push": 0.5, "in_app": 0.5, "whatsapp": 0.3},
                   ["just exploring the app"], [], "EXACT"),
}
TOPIC_TAG = {"career_anxious": "career", "marriage_seeker": "marriage", "daily_devotee": "daily",
             "curious_browser": "personality", "lapsing": "daily", "no_consent": "daily"}
PRICE = {"planet_puja": 501, "astrologer_consult": 299, "topic_reading": 199, "personality_report": 99}


def _at(d: date, hour: int, rng: random.Random) -> str:
    return datetime.combine(d, time(min(hour, 23), rng.randint(0, 59))).isoformat(timespec="seconds")


def astro_dataset(n: int = 120, seed: int = 11, today: date | None = None) -> dict[str, list[dict[str, Any]]]:
    rng = random.Random(seed)
    today = today or date.today()
    names, weights = zip(*[(k, v[0]) for k, v in ARCH.items()])
    data: dict[str, list[dict[str, Any]]] = {k: [] for k in ("customers", "sessions", "chats", "purchases", "communications", "events", "installed_apps")}
    sid = cid = pid = mid = eid = aid = 0
    for i in range(1, n + 1):
        arch = rng.choices(names, weights)[0]
        _, (h0, h1), per_week, deep_p, reads, lines, products, conf = ARCH[arch]
        place, lat, lon, lang = rng.choice(PLACES)
        first = rng.choice(FIRST)
        dob = date(rng.randint(1975, 2004), rng.randint(1, 12), rng.randint(1, 28))
        uid = f"USR-{i:04d}"
        data["customers"].append({
            "customer_id": uid, "name": f"{first} {rng.choice(LAST)}", "numerology_name": first.upper(),
            "phone": f"9{rng.randint(100000000, 999999999)}", "preferred_language": lang, "city": place.split(",")[0],
            "dob": dob.isoformat(), "birth_time": None if conf == "UNKNOWN" else f"{rng.randint(0, 23):02d}:{rng.randint(0, 59):02d}",
            "birth_time_confidence": conf, "birth_time_window_min": 30 if conf == "APPROXIMATE" else None,
            "birth_place_name": place, "birth_latitude": lat, "birth_longitude": lon, "birth_timezone": "Asia/Kolkata",
            "astro_consent_at": None if arch == "no_consent" else (today - timedelta(days=rng.randint(30, 400))).isoformat(),
            "consent_whatsapp": "yes" if rng.random() < 0.85 else "no", "consent_push": "yes" if arch != "lapsing" or rng.random() < 0.5 else "no",
            "app_signal_consent": None if arch == "no_consent" or rng.random() < 0.2 else (today - timedelta(days=rng.randint(10, 300))).isoformat(),
            "_archetype": arch,
        })
        deep_days: list[date] = []
        for d in range(60, 0, -1):
            day = today - timedelta(days=d)
            # Lapsing users were active a month ago and have nearly stopped since.
            p = per_week / 7 * ((2.0 if d > 30 else 0.25) if arch == "lapsing" else 1)
            if rng.random() < min(p, 0.95):
                deep = rng.random() < deep_p
                sid += 1
                data["sessions"].append({"session_id": f"SE-{sid:06d}", "customer_id": uid, "started_at": _at(day, rng.randint(h0, h1 - 1), rng),
                                         "minutes": rng.randint(5, 25) if deep else rng.randint(1, 4),
                                         "screen": rng.choice(["horoscope", "panchang", "chat", "report", "puja"]),
                                         "content_tag": TOPIC_TAG[arch]})
                if deep:
                    deep_days.append(day)
        for _ in range(rng.randint(1, 4) if arch not in {"lapsing", "no_consent"} else rng.randint(0, 1)):
            cid += 1
            data["chats"].append({"chat_id": f"CH-{cid:05d}", "customer_id": uid, "at": _at(today - timedelta(days=rng.randint(1, 40)), rng.randint(h0, h1 - 1), rng),
                                  "astrologer_id": rng.choice(["AS-01", "AS-02", "AS-03", "AS-04"]), "text": rng.choice(lines), "minutes": rng.randint(3, 20)})
        for _ in range(rng.randint(0, 3) if products else 0):
            prod = rng.choice(products)
            pid += 1
            data["purchases"].append({"purchase_id": f"PU-{pid:05d}", "customer_id": uid, "at": _at(today - timedelta(days=rng.randint(2, 80)), 20, rng),
                                      "product": prod, "amount": PRICE[prod]})
        # In-app events: the login funnel, screen views, CTA clicks, paywalls and checkouts.
        for d in range(30, 0, -1):
            if rng.random() > EVENT_RATE[arch]:
                continue
            day = today - timedelta(days=d)
            h = rng.randint(h0, h1 - 1)
            seq = [("app_open", None, None), ("viewed_screen", rng.choice(SCREENS[arch]), None)]
            if rng.random() < 0.25:
                seq += [("viewed_login", "login", None), ("interacted_login", "login", None)]
                if rng.random() < LOGIN_DONE[arch]:
                    seq.append(("completed_login", "login", None))
            if rng.random() < CTA_P[arch]:
                cta = rng.choice(CTAS[arch])
                seq += [("clicked_cta", "home", cta), ("viewed_paywall", "paywall", cta)]
                if rng.random() < 0.5:
                    seq.append(("started_checkout", "checkout", cta))
                    seq.append(("completed_purchase" if rng.random() < BUY_P[arch] else "abandoned_checkout", "checkout", cta))
            for name, screen, cta in seq:
                eid += 1
                data["events"].append({"event_id": f"EV-{eid:06d}", "customer_id": uid, "at": _at(day, h, rng),
                                       "event_name": name, "screen": screen or "", "cta": cta or ""})
        for cat, prob in APP_MIX[arch]:
            if rng.random() < prob:
                name, pkg = rng.choice(DEMO_APPS[cat])
                aid += 1
                data["installed_apps"].append({"install_id": f"IA-{aid:05d}", "customer_id": uid, "package_name": pkg, "app_name": name,
                                               "detected_at": (today - timedelta(days=rng.randint(0, 20))).isoformat()})

        # Messages over 8 weeks: one read in the user's own slot pulls a deep session within 1 to 2 days.
        for w in range(8, 0, -1):
            for ch, read_p in reads.items():
                if rng.random() > 0.55:
                    continue
                day = today - timedelta(days=7 * w + rng.randint(0, 3))
                in_slot = rng.random() < 0.6
                hour = rng.randint(h0, h1 - 1) if in_slot else rng.choice([8, 11, 14, 18])
                in_slot = h0 <= hour < h1
                read = rng.random() < (read_p if in_slot else read_p * 0.35)
                mid += 1
                data["communications"].append({"comm_id": f"MS-{mid:06d}", "customer_id": uid, "channel": ch, "sent_at": _at(day, hour, rng),
                                               "status": "read" if read else "delivered", "direction": "out",
                                               "offer": rng.choice(["daily_horoscope", "topic_reading", "personality_report"]), "reply_text": ""})
                if read and in_slot and rng.random() < 0.7:
                    follow = day + timedelta(days=rng.randint(0, 1))
                    sid += 1
                    data["sessions"].append({"session_id": f"SE-{sid:06d}", "customer_id": uid, "started_at": _at(follow, rng.randint(h0, h1 - 1), rng),
                                             "minutes": rng.randint(6, 20), "screen": "horoscope", "content_tag": TOPIC_TAG[arch]})
                if read and ch == "whatsapp" and rng.random() < 0.25:
                    mid += 1
                    data["communications"].append({"comm_id": f"MS-{mid:06d}", "customer_id": uid, "channel": ch, "sent_at": _at(day, min(hour + 1, 21), rng),
                                                   "status": "received", "direction": "in", "offer": "", "reply_text": rng.choice(lines)})
    return data


EVENT_RATE = {"daily_devotee": 0.9, "career_anxious": 0.5, "marriage_seeker": 0.5, "curious_browser": 0.35, "lapsing": 0.1, "no_consent": 0.3}
LOGIN_DONE = {"daily_devotee": 0.95, "career_anxious": 0.8, "marriage_seeker": 0.85, "curious_browser": 0.35, "lapsing": 0.4, "no_consent": 0.6}
CTA_P = {"daily_devotee": 0.2, "career_anxious": 0.55, "marriage_seeker": 0.5, "curious_browser": 0.25, "lapsing": 0.1, "no_consent": 0.15}
BUY_P = {"daily_devotee": 0.6, "career_anxious": 0.35, "marriage_seeker": 0.5, "curious_browser": 0.2, "lapsing": 0.1, "no_consent": 0.2}
SCREENS = {"daily_devotee": ["horoscope", "panchang", "puja"], "career_anxious": ["chat", "horoscope", "report"],
           "marriage_seeker": ["kundli_matching", "report", "chat"], "curious_browser": ["personality", "numerology", "horoscope"],
           "lapsing": ["horoscope"], "no_consent": ["horoscope", "panchang"]}
CTAS = {"daily_devotee": ["book_puja", "daily_panchang"], "career_anxious": ["talk_to_astrologer", "career_report"],
        "marriage_seeker": ["kundli_matching", "talk_to_astrologer"], "curious_browser": ["free_kundli", "personality_report"],
        "lapsing": ["free_kundli"], "no_consent": ["free_kundli"]}
APP_MIX = {
    "daily_devotee": [("spiritual", 0.8), ("payments_upi", 0.9), ("streaming_audio", 0.4), ("reproductive_health", 0.1)],
    "career_anxious": [("jobs", 0.8), ("payments_upi", 0.9), ("high_interest_loan", 0.35), ("astro_competitor", 0.4), ("education", 0.2)],
    "marriage_seeker": [("matrimony", 0.85), ("payments_upi", 0.9), ("astro_competitor", 0.3), ("dating", 0.15), ("affair_dating", 0.05)],
    "curious_browser": [("streaming_audio", 0.6), ("astro_competitor", 0.5), ("investing", 0.3), ("premium_dating", 0.05), ("payments_upi", 0.8)],
    "lapsing": [("betting", 0.4), ("high_interest_loan", 0.3), ("payments_upi", 0.7), ("travel", 0.3)],
    "no_consent": [("payments_upi", 0.8)],
}
# Demo apps per category. Affair-dating and period-tracker apps are included only to prove they get dropped.
DEMO_APPS = {
    "spiritual": [("Sri Mandir", "com.mandir"), ("Hindu Calendar - Drik Panchang", "com.drikp.core")],
    "payments_upi": [("PhonePe", "com.phonepe.app"), ("Google Pay", "com.google.android.apps.nbu.paisa.user"), ("Paytm", "net.one97.paytm")],
    "streaming_audio": [("Spotify", "com.spotify.music"), ("Pocket FM", "com.radio.pocketfm")],
    "jobs": [("Naukri", "naukriApp.appModules.login"), ("apna", "com.apnatime"), ("LinkedIn", "com.linkedin.android")],
    "high_interest_loan": [("PayMe India", "io.attabot.app.paymeindia"), ("Ram Fincorp", "com.ramfincorploan"), ("KreditBee", "com.kreditbee.android")],
    "astro_competitor": [("AstroSage", "com.ojassoft.astrosage"), ("InstaAstro", "com.instaastro.onlineastrology"), ("Vama", "com.rnselectastro")],
    "education": [("PhysicsWallah", "xyz.penpencil.physicswala"), ("Testbook", "com.testbook.tbapp")],
    "matrimony": [("Shaadi.com", "com.shaadi.android"), ("Jeevansathi", "com.jeevansathi.android"), ("Jat Shaadi", "com.jatshaadi.android"),
                  ("SC Matrimony", "")],
    "dating": [("Bumble", "com.bumble.app"), ("Aisle", "com.aisle.app")],
    "investing": [("Zerodha Kite", "com.zerodha.kite3"), ("Groww", "com.nextbillion.groww")],
    "premium_dating": [("Raya", "")],
    "betting": [("Dream11", "com.dream11.fantasy.cricket.football.kabaddi"), ("Junglee Rummy", "com.jungleerummy.playcashgameonline")],
    "travel": [("IRCTC Rail Connect", "cris.org.in.prs.ima"), ("MakeMyTrip", "com.makemytrip")],
    "affair_dating": [("Gleeden", "")],
    "reproductive_health": [("Flo", "org.iggymedia.periodtracker")],
}

DATASETS = {"astro_engagement": astro_dataset}
ID_FIELDS = {"customers": "customer_id", "sessions": "session_id", "chats": "chat_id", "purchases": "purchase_id",
             "communications": "comm_id", "events": "event_id", "installed_apps": "install_id"}
