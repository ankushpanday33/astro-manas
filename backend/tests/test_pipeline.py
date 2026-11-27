import os
import tempfile
from datetime import date

os.environ["MANAS_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["MANAS_LLM"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _run(pack: str = "astro_engagement"):
    assert client.post("/api/demo/load", json={"pack": pack, "customers": 60}).status_code == 200
    assert client.post("/api/brains/build", json={}).json()["built"] == 60
    assert client.post("/api/decide/all", json={"use_llm": False}).json()["decided"] == 60
    customers = client.get("/api/customers").json()
    for c in customers:
        one = client.get(f"/api/customers/{c['customer_id']}").json()
        d = one["decision"]
        assert d["action"] in {"contact", "hold", "human_review", "no_action"}
        if d["action"] == "contact":
            assert d["channel"] and d["send_at"] and d["message_preview"]
            assert "{" not in d["message_preview"]
        fv = {f["id"]: f["value"] for f in one["brain"]["facts"]}
        if not fv["astro_consent"]:
            assert one["brain"]["chart"] is None
            assert d["offer"] in {None, "daily_horoscope", "astrologer_consult", "resume_checkout"}
        if (fv.get("money_pressure_flag") or fv.get("gaming_exposure_flag")) and d["action"] == "contact":
            # Protect-only app signals: the final offer is never a paid one.
            assert d["offer"] not in {"astrologer_consult", "planet_puja", "topic_reading", "personality_report", "resume_checkout"}, d["reason"]
        if not fv.get("app_signal_consent"):
            assert not fv.get("app_interests") and not fv.get("money_pressure_flag")
        if fv.get("anxiety_flag") and d["action"] == "contact":
            # The Wellbeing Advocate's stance must be a free offer for an anxious user.
            adv = next(s for s in d["council"]["stances"] if s["speaker"] == "customer_advocate")
            assert d["twin"]["candidates"][adv["choice"]]["tone"] not in {"astrologer_consult", "planet_puja", "topic_reading", "personality_report"}
        net = client.get(f"/api/customers/{c['customer_id']}/network").json()
        assert any(n["id"] == "decision" and n["path"] for n in net["nodes"])
    assert client.post("/api/outcomes/simulate").status_code == 200
    return customers


def test_astro_pipeline():
    customers = _run()
    with_chart = next(c for c in customers if c["headline"]["radical"])
    astro = client.get(f"/api/customers/{with_chart['customer_id']}/astro").json()
    assert "birth_latitude" not in astro["groups"]["A"]
    assert astro["groups"]["C"]["gemstone_prescription"] == "REQUIRES_KUNDLI_REVIEW"
    trial = client.post(f"/api/customers/{with_chart['customer_id']}/name-trial", json={"spelling": "RAAVI"}).json()
    assert trial["trial"]["compound"] == 11 and trial["trial"]["value"] == 2


def test_relative_dates():
    from app.brain.memory import resolve_date
    assert resolve_date("interview next week", date(2026, 10, 2)) == date(2026, 10, 9)
    assert resolve_date("kal result hai", date(2026, 10, 2)) == date(2026, 10, 3)
