import os
import tempfile

os.environ.setdefault("MANAS_DB", os.path.join(tempfile.mkdtemp(), "ingest.db"))
os.environ["MANAS_LLM"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _up(source, name, content, mode="append"):
    return client.post(f"/api/ingest/{source}", files={"file": (name, content)}, data={"mode": mode, "pack": "astro_engagement"})


def test_upload_users_and_build_charts():
    client.post("/api/data/reset", json={"confirm": True})
    csv = (b"User ID,Full Name,Date of Birth,Time of Birth,Place of Birth,Astro Consent,Language\n"
           b"U1,Ravi Kumar,24/06/2000,10:35,Lucknow,yes,Hindi\n"
           b"U2,Sita Devi,05/01/1992,,Pune,yes,Marathi\n"
           b"U3,No Consent,12/12/1990,08:00,Delhi,no,English\n"
           b"U4,Bad Date,31/02/1990,08:00,Delhi,yes,English\n")
    r = _up("customers", "users.csv", csv).json()
    assert r["loaded"] == 3 and r["skipped"] == 1 and "not a date" in r["skipped_rows"][0]["reason"]
    u1 = r["preview"][0]
    assert u1["dob"] == "2000-06-24" and u1["birth_latitude"] == 26.8467 and u1["numerology_name"] == "RAVI"
    chats = b"customer_id,at,text\nU1,20/11/2026 19:00,job interview next week bahut tension hai\n"
    assert _up("chats", "chats.csv", chats).json()["loaded"] == 1
    assert client.post("/api/brains/build", json={}).json()["built"] == 3
    client.post("/api/decide/all", json={})
    a1 = client.get("/api/customers/U1/astro").json()
    assert a1["groups"]["B"]["radical_number"] == 6 and a1["groups"]["B"]["name_number"] == 1
    assert a1["groups"]["F"]["nakshatra_name"]
    a2 = client.get("/api/customers/U2/astro").json()
    assert a2["groups"]["F"]["nakshatra_name"] is None  # no birth time, no Panchang
    assert client.get("/api/customers/U3/astro").status_code == 404  # no consent, nothing computed
    # Re-upload with a corrected DOB: the chart is recomputed, not served stale.
    _up("customers", "fix.csv", b"customer_id,name,dob,birth_time,birth_place_name,astro_consent_at\nU1,Ravi Kumar,19/06/2000,10:35,Lucknow,yes\n")
    client.post("/api/brains/build", json={})
    assert client.get("/api/customers/U1/astro").json()["groups"]["B"]["radical_number"] == 1


def test_schema_lists_astro_sources():
    s = client.get("/api/ingest/schema").json()
    assert {x["source"] for x in s["sources"]} == {"customers", "sessions", "chats", "purchases", "communications", "events", "installed_apps"}
    assert "dob" in next(x for x in s["sources"] if x["source"] == "customers")["required"]


def test_installed_apps_are_minimised_at_upload():
    client.post("/api/data/reset", json={"confirm": True})
    _up("customers", "u.csv", b"customer_id,name,dob,astro_consent_at,app_consent\nA1,Ravi Kumar,24/06/2000,yes,yes\nA2,Sita Devi,05/01/1992,yes,no\n")
    apps = (b"customer_id,package,app\n"
            b"A1,com.shaadi.android,Shaadi.com\n"
            b"A1,com.jatshaadi.android,Jat Shaadi\n"
            b"A1,,Gleeden\n"
            b"A1,org.iggymedia.periodtracker,Flo\n"
            b"A1,io.attabot.app.paymeindia,PayMe India\n"
            b"A1,com.some.unknown,Unknown App\n"
            b"A2,com.naukri.fake,Naukri\n")
    r = _up("installed_apps", "apps.csv", apps).json()
    reasons = " | ".join(x["reason"] for x in r["skipped_rows"])
    assert r["loaded"] == 4, r
    assert "Extramarital dating: discarded" in reasons and "Period / fertility / pregnancy: discarded" in reasons
    assert "untracked apps are never stored" in reasons
    names = [p["app_name"] for p in r["preview"]]
    assert "Matrimony app (community not stored)" in names and "Jat Shaadi" not in str(r["preview"])

    events = b"customer_id,event,event_time,cta\n" + b"".join(
        f"A1,{e},2{6 - i % 5}/11/2026 20:0{i % 9},talk_to_astrologer\n".encode() for i, e in enumerate(
            ["viewed_login", "interacted_login", "completed_login", "clicked_cta", "viewed_paywall", "started_checkout",
             "abandoned_checkout", "clicked_cta", "viewed_paywall"]))
    assert _up("events", "events.csv", events).json()["loaded"] == 9
    client.post("/api/brains/build", json={})
    client.post("/api/decide/all", json={})
    b1 = client.get("/api/customers/A1").json()
    fv = {f["id"]: f["value"] for f in b1["brain"]["facts"]}
    assert fv["app_topic_hint"] == "marriage" and fv["money_pressure_flag"] is True
    assert b1["brain"]["predictions"]["purchase_propensity_7d"]["status"] == "ok"
    # Money pressure is protect-only: no paid offer goes out, even with an abandoned checkout.
    assert b1["decision"]["offer"] not in {"astrologer_consult", "planet_puja", "topic_reading", "personality_report", "resume_checkout"}
    fv2 = {f["id"]: f["value"] for f in client.get("/api/customers/A2").json()["brain"]["facts"]}
    assert fv2["app_signal_consent"] is False and not fv2.get("app_interests")
