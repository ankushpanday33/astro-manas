"""Generate a deliberately messy 100-user test set for the Upload data page. Every person is fictional.

Run:  python scripts/make_hard_dataset.py   (writes test-data/hard-100/)

Each file uses a different format and its own column names, and plants the traps listed in TRAPS.md.
"""
from __future__ import annotations

import csv
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook

OUT = Path(__file__).resolve().parent.parent / "test-data" / "hard-100"
rng = random.Random(2026)
TODAY = date.today()

FIRST = ["Aarav", "Priya", "Rohit", "Sneha", "Vikram", "Anjali", "Karan", "Pooja", "Arjun", "Neha", "Kavya", "Imran", "Lakshmi",
         "Deepak", "Sunita", "Manoj", "Asha", "Nikhil", "Divya", "Sanjay", "Rekha", "Amit", "Harsh", "Nisha", "Tarun", "Swati"]
LAST = ["Sharma", "Verma", "Patel", "Iyer", "Reddy", "Singh", "Das", "Nair", "Joshi", "Gupta", "Mehta", "Kulkarni", "Banerjee", "Yadav"]
DEVANAGARI = ["रवि कुमार", "सीमा देवी", "अनिल शर्मा"]
PLACES = ["Lucknow", "New Delhi, IN", "Bengaluru", "Bangalore", "Mumbai", "Pune", "Jaipur", "Kolkata", "Chennai", "Varanasi",
          "Gorakhpur", "Ujjain", "Hyderabad"]          # Gorakhpur and Ujjain are not in the built-in geocoder
LANGS = ["Hindi", "hindi", "HINDI", "Marathi", "Tamil", "Bengali", "English", "Telugu", ""]
PERSONAS = ["career_anxious", "marriage_seeker", "devotee", "curious", "money_stress", "gamer", "lapsing", "opted_out"]


def dob_text(d: date, i: int) -> str:
    fmt = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"][i % 4]
    return d.strftime(fmt)


def time_text(i: int) -> str:
    h, m = rng.randint(0, 23), rng.randint(0, 59)
    style = i % 7
    if style == 0:
        return f"{h:02d}:{m:02d}"
    if style == 1:
        return datetime(2000, 1, 1, h, m).strftime("%I:%M %p").lstrip("0")   # 6:20 PM
    if style == 2:
        return f"{h:02d}:{m:02d}:00"
    if style == 3:
        return f"{h}.{m:02d}"                                                  # 18.45
    if style == 4:
        return ""
    if style == 5:
        return "unknown"
    return datetime(2000, 1, 1, h, m).strftime("%I:%M%p").lower()              # 06:20pm


def consent_text(i: int) -> str:
    return ["yes", "Yes", "Y", "TRUE", "1", "no", "", "2026-05-01", "agree", "No"][i % 10]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    users, persona = [], {}
    for i in range(1, 101):
        uid = f"U{i:03d}"
        persona[uid] = PERSONAS[i % len(PERSONAS)]
        d = date(rng.randint(1970, 2005), rng.randint(1, 12), rng.randint(1, 28))
        name = DEVANAGARI[i % 3] if i % 33 == 0 else (f"Dr. {rng.choice('AKSRV')}. {rng.choice(LAST)}" if i % 41 == 0
                                                       else f"{rng.choice(FIRST)} {rng.choice(LAST)}")
        row = {"User ID": f" {uid} " if i % 12 == 0 else uid, "Full Name": name, "Date of Birth": dob_text(d, i),
               "Time of Birth": time_text(i), "Place of Birth": PLACES[i % len(PLACES)], "Astro Consent": consent_text(i),
               "App Consent": consent_text(i + 3), "Language": LANGS[i % len(LANGS)], "Mobile": f"+91 9{rng.randint(100000000, 999999999)}",
               "Lat": "", "Lon": "", "Notes": "VIP" if i % 17 == 0 else ""}
        if PLACES[i % len(PLACES)] == "Ujjain" and i % 2 == 0:
            row["Lat"], row["Lon"] = "23.1765", "75.7885"                      # explicit coordinates rescue an unknown city
        users.append(row)
    # Traps in the people file
    users[9]["Date of Birth"] = "31/02/1990"            # impossible date
    users[19]["Date of Birth"] = "not known"            # free text
    users[29]["Date of Birth"] = "12/12/1890"           # implausible year
    users[39]["Date of Birth"] = ""                     # missing required value
    users[44]["Time of Birth"] = "25:61"                # impossible time
    users.append(dict(users[49], **{"Full Name": users[49]["Full Name"] + " (updated)"}))   # duplicate id U050, later row wins
    users.append({k: "" for k in users[0]})             # an empty row
    with open(OUT / "1_users.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(users[0].keys()))
        w.writeheader()
        w.writerows(users)

    ids = [f"U{i:03d}" for i in range(1, 101)]

    # Sessions: NDJSON, mixed timestamp formats, bad minutes
    with open(OUT / "2_sessions.ndjson", "w", encoding="utf-8") as f:
        for uid in ids:
            p = persona[uid]
            n = {"devotee": 40, "lapsing": 4, "opted_out": 3}.get(p, 14)
            for k in range(n):
                day = TODAY - timedelta(days=rng.randint(1, 55) if p != "lapsing" else rng.randint(35, 60))
                ts = datetime.combine(day, datetime.min.time()) + timedelta(hours=rng.randint(6, 22), minutes=rng.randint(0, 59))
                when = ts.isoformat() if k % 3 else ts.strftime("%d/%m/%Y %H:%M")
                mins = rng.choice(["12", "3", "", "abc", 7, 25, "1"])
                f.write(json.dumps({"uid": uid, "opened_at": when, "duration": mins, "screen": rng.choice(["Horoscope", "panchang", "CHAT"])}) + "\n")

    # Chats: semicolon CSV, Hinglish, emojis, lowercase ids (orphans), relative dates
    lines = {"career_anxious": ["job interview next week hai, bahut tension 😟", "naukri kab lagegi? pareshan hoon"],
             "marriage_seeker": ["shaadi kab hogi? rishta dekh rahe hain", "kundli matching chahiye"],
             "devotee": ["aaj ka din kaisa rahega 🙏", "which colour is good today"],
             "curious": ["what does my nakshatra mean?", "mera lucky number kya hai"],
             "money_stress": ["paise ki bahut tension hai, kuch upay batao", "loan ka EMI bhar nahi pa raha, worried"],
             "gamer": ["aaj mera lucky number kya hai, khelna hai", "kal match hai"],
             "lapsing": ["notifications band karo please"], "opted_out": ["stop sending messages", "mat bhejo"]}
    with open(OUT / "3_chats.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Cust ID", "Asked On", "Question", "Astrologer"])
        for uid in ids:
            for text in rng.sample(lines[persona[uid]], k=min(2, len(lines[persona[uid]]))):
                day = TODAY - timedelta(days=rng.randint(0, 20))
                cid = uid.lower() if uid in ("U015", "U016") else uid
                w.writerow([cid, day.strftime("%d-%m-%Y"), text, rng.choice(["AS-01", "AS-02", "AS-03"])])
        w.writerow(["U999", TODAY.strftime("%d/%m/%Y"), "who am I", "AS-01"])     # orphan: no such user

    # Purchases: JSON array, rupee strings
    purchases = []
    for uid in ids:
        if persona[uid] in {"marriage_seeker", "career_anxious", "devotee"} and rng.random() < 0.6:
            for _ in range(rng.randint(1, 3)):
                purchases.append({"customer_id": uid, "purchased_at": (TODAY - timedelta(days=rng.randint(3, 80))).strftime("%d/%m/%Y"),
                                  "product": rng.choice(["astrologer_consult", "topic_reading", "planet_puja", "Kundli Report PDF"]),
                                  "amount": rng.choice(["₹299", "199.00", 501, "₹1,100", ""])})
    (OUT / "4_purchases.json").write_text(json.dumps(purchases, ensure_ascii=False, indent=1), encoding="utf-8")

    # Messages: tab-separated, inconsistent channel and status spellings
    with open(OUT / "5_messages.tsv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["msg_id", "customer_id", "Medium", "Sent On", "Delivery Status", "direction", "reply"])
        mid = 0
        for uid in ids:
            for k in range(rng.randint(4, 12)):
                mid += 1
                day = TODAY - timedelta(days=rng.randint(1, 56))
                hour = rng.randint(8, 21)
                ch = rng.choice(["WhatsApp", "whatsapp", "Push Notification", "push", "In-App", "in_app", "SMS"])
                st = rng.choice(["Read", "DELIVERED", "read", "failed", "Seen"])
                w.writerow([f"M{mid:05d}", uid, ch, f"{day.strftime('%d/%m/%Y')} {hour}:{rng.randint(0, 59):02d}", st, "out", ""])
                if st.lower() in {"read", "seen"} and rng.random() < 0.2:
                    mid += 1
                    w.writerow([f"M{mid:05d}", uid, ch, f"{day.strftime('%d/%m/%Y')} {min(hour + 1, 22)}:05", "received", "in",
                                rng.choice(lines[persona[uid]])])

    # Events: Excel, human-readable names, real Excel datetimes mixed with 12-hour strings
    wb = Workbook()
    ws = wb.active
    ws.title = "events"
    ws.append(["User Id", "Event", "Event Time", "Button Name", "Screen"])
    flows = {"career_anxious": "talk_to_astrologer", "marriage_seeker": "kundli_matching", "devotee": "book_puja", "curious": "personality_report",
             "money_stress": "talk_to_astrologer", "gamer": "free_kundli", "lapsing": "free_kundli", "opted_out": "free_kundli"}
    for uid in ids:
        p = persona[uid]
        days = {"devotee": 25, "lapsing": 1, "opted_out": 2}.get(p, 10)
        for _ in range(days):
            day = TODAY - timedelta(days=rng.randint(1, 29))
            base = datetime.combine(day, datetime.min.time()) + timedelta(hours=rng.randint(8, 21))
            seq = ["App Open", "Viewed Screen"]
            if rng.random() < 0.3:
                seq += ["Viewed Login", "Interacted Login"] + (["Completed Login"] if rng.random() < 0.6 else [])
            if rng.random() < 0.5:
                seq += ["Clicked CTA", "Viewed Paywall", "Started Checkout",
                        "Abandoned Checkout" if p in {"curious", "money_stress", "career_anxious"} and rng.random() < 0.6 else "Completed Purchase"]
            for j, ev in enumerate(seq):
                t = base + timedelta(minutes=j)
                ws.append([uid if j % 5 else uid.lower(), ev if j % 2 else ev.lower().replace(" ", "_"),
                           t if j % 3 else t.strftime("%d/%m/%Y %I:%M %p"), flows[p] if "CTA" in ev or "Check" in ev or "Paywall" in ev else "",
                           "home"])
    wb.save(OUT / "6_events.xlsx")

    # Installed apps: package and/or name, sensitive and untracked apps mixed in
    mix = {"career_anxious": [("naukriApp.appModules.login", "Naukri"), ("com.ojassoft.astrosage", "AstroSage")],
           "marriage_seeker": [("com.shaadi.android", "Shaadi.com"), ("com.jatshaadi.android", "Jat Shaadi"), ("", "SC Matrimony")],
           "devotee": [("com.mandir", "Sri Mandir"), ("org.iggymedia.periodtracker", "Flo")],
           "curious": [("com.spotify.music", "Spotify"), ("", "Raya"), ("com.whatsapp", "WhatsApp")],
           "money_stress": [("io.attabot.app.paymeindia", "PayMe India"), ("com.ramfincorploan", "Ram Fincorp"), ("com.phonepe.app", "PhonePe")],
           "gamer": [("com.dream11.fantasy.cricket.football.kabaddi", "Dream11"), ("", "Gleeden")],
           "lapsing": [("com.jungleerummy.playcashgameonline", "Junglee Rummy")], "opted_out": [("com.phonepe.app", "PhonePe")]}
    with open(OUT / "7_installed_apps.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["user_id", "package", "app", "seen_at"])
        for uid in ids:
            for pkg, name in mix[persona[uid]]:
                w.writerow([uid, pkg, name, (TODAY - timedelta(days=rng.randint(0, 10))).strftime("%d/%m/%Y")])
        w.writerow(["U001", "", "", "27/11/2026"])                       # no package and no name
    (OUT / "personas_answer_key.json").write_text(json.dumps(persona, indent=1), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
