"""Installed-app signals: which apps we look for, what each category may tell the brain, and what it may never do.

Every category has a USE tier:
  personalise - may shape offers and timing (matrimony, jobs, investing, travel, competitor astro apps, ...)
  protect     - may ONLY protect the user: no paid upsell, calmer copy, lower frequency (high-interest loans, betting)
  discard     - dropped at upload, never stored, never inferred (affair dating, period / fertility / pregnancy)

Hard rules:
  - Nothing is computed without app_signal_consent on the user (DPDP Act; Google Play User Data policy treats app
    inventory as personal and sensitive data and requires prominent disclosure and consent).
  - No label about a person's character, fidelity, sexuality, health, caste or religion is ever produced.
  - Community / caste matrimony apps count only as "matrimony"; the community is never stored.
  - Packages marked verified=False come from third-party trackers; detection also matches on the app name.

Package names for most apps are copied from the Astrotalk installed-app analysis (23/11/2026, APK static analysis).
"""
from __future__ import annotations

from typing import Any

CATEGORIES: dict[str, dict[str, Any]] = {
    "matrimony": {"label": "Matrimony", "use": "personalise", "topic": "marriage",
                  "logic": "Actively looking for a life partner: marriage readings and Kundli matching are relevant now.",
                  "offer_boost": {"topic_reading": 0.07, "astrologer_consult": 0.04}},
    "dating": {"label": "Dating (mainstream)", "use": "personalise", "topic": "relationships",
               "logic": "Open to new relationships: compatibility and relationship guidance may interest them. Never inferred: orientation or intimacy.",
               "offer_boost": {"topic_reading": 0.04}},
    "premium_dating": {"label": "Premium / celebrity dating", "use": "personalise", "topic": "relationships",
                       "logic": "Invitation-only community member: likely values premium, private service. Offer a senior astrologer, not discounts.",
                       "offer_boost": {"astrologer_consult": 0.05}, "premium": True},
    "affair_dating": {"label": "Extramarital dating", "use": "discard",
                      "logic": "Discarded at upload. Fidelity is never inferred, stored or used."},
    "reproductive_health": {"label": "Period / fertility / pregnancy", "use": "discard",
                            "logic": "Discarded at upload. Health and reproductive data is never inferred, stored or used."},
    "high_interest_loan": {"label": "Instant / high-interest loans", "use": "protect",
                           "logic": "Possible short-term money pressure. Protect only: no paid upsell, no 'remedy for debt' offers, free guidance first."},
    "betting": {"label": "Betting / fantasy / rummy", "use": "protect",
                "logic": "Exposure to real-money gaming. Protect only: never share 'lucky numbers for betting', no paid upsell, calm copy."},
    "mainstream_credit": {"label": "Credit cards / credit score", "use": "personalise", "topic": "finance",
                          "logic": "Manages credit actively: finance and career-money readings are relevant.", "offer_boost": {}},
    "payments_upi": {"label": "UPI / wallet", "use": "personalise",
                     "logic": "Pays by UPI: send a UPI deep link at checkout.", "offer_boost": {}, "payment_ready": True},
    "investing": {"label": "Investing / trading / crypto", "use": "personalise", "topic": "finance",
                  "logic": "Follows markets: finance-timing (muhurat) content fits. Never promise financial outcomes.",
                  "offer_boost": {"topic_reading": 0.04}},
    "jobs": {"label": "Jobs / career", "use": "personalise", "topic": "career",
             "logic": "Job hunting or switching: career readings and interview-day guidance fit.",
             "offer_boost": {"topic_reading": 0.06, "astrologer_consult": 0.03}},
    "education": {"label": "Exam prep / education", "use": "personalise", "topic": "education",
                  "logic": "Preparing for exams: study-timing and exam-day guidance fit.", "offer_boost": {"topic_reading": 0.04}},
    "astro_competitor": {"label": "Other astrology apps", "use": "personalise",
                         "logic": "Already pays for astrology elsewhere: a free first consult with a matched astrologer wins them over.",
                         "offer_boost": {"astrologer_consult": 0.06}},
    "spiritual": {"label": "Devotional / meditation", "use": "personalise",
                  "logic": "Devotional habit: daily Panchang, mantra and puja content fit.",
                  "offer_boost": {"planet_puja": 0.05, "daily_horoscope": 0.03}},
    "travel": {"label": "Travel", "use": "personalise", "logic": "Travels often: travel-muhurat content fits.", "offer_boost": {}},
    "streaming_audio": {"label": "Music / audio", "use": "personalise",
                        "logic": "Audio-first: an audio horoscope or mantra suits them.", "offer_boost": {"daily_horoscope": 0.02}},
}

# (name, package, category, verified)
APPS: list[tuple[str, str, str, bool]] = [
    # Matrimony (PDF) + community apps (counted as matrimony only, community never stored)
    *[(n, p, "matrimony", True) for n, p in [
        ("BharatMatrimony", "com.bharatmatrimony"), ("Shaadi.com", "com.shaadi.android"), ("Jeevansathi", "com.jeevansathi.android"),
        ("Sangam.com", "com.communityshaadi.android"), ("M4marry", "com.manoramaonline.m4marry"),
        ("Kundli Milan - Vivah Matching (Nithra)", "nithra.horoscope.marriage.vivah.matching"),
        ("Assamese Matrimony", "com.assamesematrimony"), ("Bengali Matrimony", "com.bengalimatrimony"),
        ("Bhojpuri Matrimony", "com.bhojpurimatrimony"), ("Bihari Matrimony", "com.biharimatrimony"),
        ("Gujarati Matrimony", "com.gujaratimatrimony"), ("Hindi Matrimony", "com.hindimatrimony"),
        ("Kannada Matrimony", "com.kannadamatrimony"), ("Kerala Matrimony", "com.keralamatrimony"),
        ("Marathi Matrimony", "com.marathimatrimony"), ("Marwadi Matrimony", "com.marwadimatrimony"),
        ("Oriya Matrimony", "com.oriyamatrimony"), ("Punjabi Matrimony", "com.punjabimatrimony"),
        ("Rajasthani Matrimony", "com.rajasthanimatrimony"), ("Sindhi Matrimony", "com.sindhimatrimony"),
        ("Tamil Matrimony", "com.tamilmatrimony"), ("Telugu Matrimony", "com.telugumatrimony"),
        ("Jat Shaadi", "com.jatshaadi.android"), ("Jat Rishtey", "com.webratech.jatrishtey")]],
    ("Jat Matrimony", "", "matrimony", False), ("SC Matrimony", "", "matrimony", False),
    # Dating (PDF)
    *[(n, p, "dating", True) for n, p in [
        ("Aisle", "com.aisle.app"), ("Badoo", "com.badoo.mobile"), ("Betterhalf", "com.betterhalf"), ("Boo", "boo.enterprises.dating.boo"),
        ("Bumble", "com.bumble.app"), ("Coffee Meets Bagel", "com.coffeemeetsbagel"), ("Dil Mil", "co.dilmil.android"),
        ("eharmony", "com.eharmony"), ("Frnd", "com.dating.for.all"), ("Happn", "com.ftw_and_co.happn"), ("Hily", "com.hily.app"),
        ("Hinge", "co.hinge.app"), ("Jodi365", "com.freeelective.jodi365"), ("Jodii", "jodii.app"),
        ("Match", "com.match.android.matchmobile"), ("OkCupid", "com.okcupid.okcupid"), ("Plenty of Fish", "com.pof.android"),
        ("QuackQuack", "com.quackquack"), ("Tinder", "com.tinder"), ("TrulyMadly", "com.trulymadly.android.app"), ("Zoosk", "com.zoosk.zoosk")]],
    ("Raya", "", "premium_dating", False),
    ("Gleeden", "", "affair_dating", False), ("Slush", "", "affair_dating", False), ("Ashley Madison", "", "affair_dating", False),
    # Period / fertility / pregnancy (PDF): discarded
    *[(n, p, "reproductive_health", True) for n, p in [
        ("BabyCenter", "com.babycenter.pregnancytracker"), ("Clue", "com.clue.android"), ("Flo", "org.iggymedia.periodtracker"),
        ("Glow", "com.glow.android"), ("Healofy", "com.healofy"), ("Maya (Plackal)", "in.plackal.lovecyclesfree"),
        ("Mylo", "in.mylo.pregnancy.baby.app"), ("Ovia Fertility", "com.ovuline.fertility"), ("Ovia Pregnancy", "com.ovuline.pregnancy"),
        ("Period Calendar (Simple Design)", "com.popularapp.periodcalendar"), ("Pregnancy+", "com.hp.pregnancy.lite"),
        ("Premom", "premom.eh.com.ehpremomapp"), ("theAsianparent", "com.tickledmedia.ParentTown"), ("What to Expect", "com.wte.view")]],
    # Instant / high-interest loans: protect only
    ("PayMe India", "io.attabot.app.paymeindia", "high_interest_loan", False),
    ("Ram Fincorp", "com.ramfincorploan", "high_interest_loan", False),
    ("Ram Fincorp: Personal Loan App", "com.personalloanramfin", "high_interest_loan", False),
    ("Ram Fincorp: Express", "com.ramfinexpress", "high_interest_loan", False),
    ("Ram Fincorp Loan", "com.ramfinloan", "high_interest_loan", False),
    *[(n, p, "high_interest_loan", True) for n, p in [
        ("KreditBee", "com.kreditbee.android"), ("mPokket", "com.mpokket.app"), ("CASHe", "co.tslc.cashe.android"),
        ("Fibe (EarlySalary)", "com.earlysalary.android"), ("Stashfin", "com.stashfin.android"), ("MoneyTap (Freo)", "com.mycash.moneytap.app"),
        ("PaySense", "com.gopaysense.android.boost"), ("Moneyview", "com.whizdm.moneyview.loans"), ("Kissht", "com.fastbanking"),
        ("True Balance", "com.balancehero.truebalance"), ("Home Credit", "com.portal.hcin"), ("Bullet", "money.bullet")]],
    # Betting / fantasy / rummy: protect only (Indian-market subset from the PDF)
    *[(n, p, "betting", True) for n, p in [
        ("Dream11", "com.dream11.fantasy.cricket.football.kabaddi"), ("My11Circle", "com.games24x7.my11circle.fantasycricket"),
        ("MPL", "com.mpl.androidapp.cash"), ("WinZO", "com.winzo.platform"), ("Zupee", "com.zupee.free"), ("A23 Rummy", "in.a23.rummy"),
        ("Junglee Rummy", "com.jungleerummy.playcashgameonline"), ("RummyCircle", "com.games24x7.rummycircle.ultimaterummy"),
        ("PokerBaazi", "com.baazigames.pokerbaazi.practice"), ("Teen Patti Gold", "com.teenpatti.hd.gold"), ("1xBet", "org.xbet.client1"),
        ("Melbet", "org.melbet.client"), ("ProBO", "com.proboyesno.newprobo"), ("Pocket52", "com.nirdesagames")]],
    # Mainstream credit
    *[(n, p, "mainstream_credit", True) for n, p in [
        ("CRED", "com.dreamplug.androidapp"), ("OneCard", "com.creditcard.onecard"), ("Scapia", "cards.scapia.android"),
        ("CIBIL Score & Report", "com.tuci.cibilindia"), ("OneScore", "tech.fplabs.score"), ("slice", "indwin.c3.shareapp"),
        ("SBI Card", "com.ge.capital.konysbiapp")]],
    # UPI / wallets
    *[(n, p, "payments_upi", True) for n, p in [
        ("Google Pay", "com.google.android.apps.nbu.paisa.user"), ("PhonePe", "com.phonepe.app"), ("Paytm", "net.one97.paytm"),
        ("BHIM", "in.org.npci.upiapp"), ("Mobikwik", "com.mobikwik_new"), ("Freecharge", "com.freecharge.android"),
        ("Amazon", "in.amazon.mShop.android.shopping")]],
    # Investing / trading / crypto
    *[(n, p, "investing", True) for n, p in [
        ("Zerodha Kite", "com.zerodha.kite3"), ("Groww", "com.nextbillion.groww"), ("Upstox", "in.upstox.app"), ("Angel One", "com.msf.angelmobile"),
        ("Dhan", "com.dhan.live"), ("Paytm Money", "com.paytmmoney"), ("smallcase", "com.smallcase.android"), ("CoinDCX", "com.coindcx.btc"),
        ("WazirX", "com.wrx.wazirx"), ("CoinSwitch", "com.coinswitch.kuber"), ("Binance", "com.binance.dev")]],
    # Jobs and education
    *[(n, p, "jobs", True) for n, p in [
        ("Naukri", "naukriApp.appModules.login"), ("Indeed", "com.indeed.android.jobsearch"), ("apna", "com.apnatime"),
        ("LinkedIn", "com.linkedin.android"), ("foundit", "com.monsterindia.seeker.views"), ("WorkIndia", "in.workindia.nileshdungarwal.workindiaandroid"),
        ("Internshala", "com.internshala.app"), ("Glassdoor", "com.glassdoor.app")]],
    *[(n, p, "education", True) for n, p in [
        ("PhysicsWallah", "xyz.penpencil.physicswala"), ("Unacademy", "com.unacademyapp"), ("Testbook", "com.testbook.tbapp"),
        ("Adda247", "com.adda247.app"), ("BYJU'S", "com.byjus.thelearningapp"), ("Vedantu", "com.vedantu.app"), ("StudyIQ", "com.studyiq.android")]],
    # Competitor astrology apps
    *[(n, p, "astro_competitor", True) for n, p in [
        ("AstroSage", "com.ojassoft.astrosage"), ("Astroyogi", "com.netway.phone.advice"), ("InstaAstro", "com.instaastro.onlineastrology"),
        ("Anytime Astro", "com.dashaspeaks.astrology.online.chat"), ("AstroChat.com", "com.peoplegroup.astrouser"), ("Vama", "com.rnselectastro"),
        ("GaneshaSpeaks", "app.ganeshaspeaks.kundli.astrology.horoscope.astro.vedic.jyotish.astrologer.prediction.zodiac"),
        ("Co-Star", "com.costarastrology"), ("Clickastro Astrology", "com.clickastro.freehoroscope.astrology"), ("Melooha", "com.melooha.app"),
        ("Kundli SuperApp", "com.astrobix.kundli"), ("Nebula", "genesis.nebula"), ("Gurudev", "com.astrology.gurudev"), ("Panditji", "com.astrology.panditji")]],
    # Devotional / meditation
    *[(n, p, "spiritual", True) for n, p in [
        ("Sri Mandir", "com.mandir"), ("Hindu Calendar - Drik Panchang", "com.drikp.core"), ("Sadhguru - Yoga & Meditation", "com.ishafoundation.app"),
        ("Art of Living", "com.sspt.aol"), ("TTDevasthanams", "com.ttdapp"), ("Mata Vaishnodevi App", "com.matavaishnodevi.myprayer"),
        ("Bhakti: Gita & Mantras (Kuku)", "com.vlv.aravali.bhakti"), ("Heartfulness", "org.heartfulness.heartintune.prod")]],
    # Travel and audio
    *[(n, p, "travel", True) for n, p in [
        ("MakeMyTrip", "com.makemytrip"), ("IRCTC Rail Connect", "cris.org.in.prs.ima"), ("ixigo Trains", "com.ixigo.train.ixitrain"),
        ("IndiGo", "in.goindigo.android"), ("redBus", "in.redbus.android"), ("Goibibo", "com.goibibo")]],
    *[(n, p, "streaming_audio", True) for n, p in [
        ("Spotify", "com.spotify.music"), ("JioSaavn", "com.jio.media.jiobeats"), ("Gaana", "com.gaana"), ("Wynk Music", "com.bsbportal.music"),
        ("Pocket FM", "com.radio.pocketfm"), ("Kuku FM", "com.vlv.aravali")]],
]

BY_PACKAGE = {p.lower(): (n, c, v) for n, p, c, v in APPS if p}
BY_NAME = {n.lower(): (n, c, v) for n, p, c, v in APPS}


def classify(package: str | None, name: str | None) -> dict[str, Any] | None:
    """Match an installed app by package first, then by exact name. Returns None for apps we do not track."""
    hit = BY_PACKAGE.get((package or "").strip().lower()) or BY_NAME.get((name or "").strip().lower())
    if not hit:
        return None
    app_name, cat, verified = hit
    return {"app_name": app_name, "category": cat, "use": CATEGORIES[cat]["use"], "verified_package": verified}


def catalog_summary() -> list[dict[str, Any]]:
    out = []
    for cid, c in CATEGORIES.items():
        apps = [n for n, p, cat, v in APPS if cat == cid]
        out.append({"category": cid, "label": c["label"], "use": c["use"], "logic": c["logic"], "apps": len(apps),
                    "examples": apps[:6] if c["use"] != "discard" else apps[:3]})
    return out


COMMUNITY_HINTS = ("jat", "sc matrimony", "bhojpuri", "marwadi", "sindhi", "bihari", "rajasthani", "community")


def scrub_row(r: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Data minimisation at the door. Returns (row to store, None) or (None, reason it was dropped)."""
    hit = classify(r.get("package_name"), r.get("app_name"))
    if not hit:
        return None, "not in the tracked catalog: untracked apps are never stored"
    if hit["use"] == "discard":
        return None, f"{CATEGORIES[hit['category']]['label']}: discarded by privacy policy, never stored"
    out = {k: v for k, v in r.items() if k not in {"app_name", "package_name"}}
    out.update(category=hit["category"], use=hit["use"], verified_package=hit["verified_package"])
    if hit["category"] == "matrimony" and any(h in hit["app_name"].lower() for h in COMMUNITY_HINTS):
        out.update(app_name="Matrimony app (community not stored)", package_name="")
    else:
        out.update(app_name=hit["app_name"], package_name=r.get("package_name") or "")
    return out, None
