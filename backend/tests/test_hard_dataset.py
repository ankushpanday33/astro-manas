"""The messy 100-user set in test-data/hard-100 must upload, build and decide with no failures."""
import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MANAS_DB", os.path.join(tempfile.mkdtemp(), "hard.db"))
os.environ["MANAS_LLM"] = "0"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "test-data" / "hard-100"
FILES = [("customers", "1_users.csv"), ("sessions", "2_sessions.ndjson"), ("chats", "3_chats.csv"), ("purchases", "4_purchases.json"),
         ("communications", "5_messages.tsv"), ("events", "6_events.xlsx"), ("installed_apps", "7_installed_apps.csv")]
PAID = {"astrologer_consult", "planet_puja", "topic_reading", "personality_report", "resume_checkout"}


def test_hard_dataset_end_to_end():
    c = TestClient(app)
    c.post("/api/data/reset", json={"confirm": True})
    reports = {}
    for source, name in FILES:
        r = c.post(f"/api/ingest/{source}", files={"file": (name, (DATA / name).read_bytes())}, data={"mode": "append", "pack": "astro_engagement"})
        assert r.status_code == 200, (name, r.text)
        reports[source] = r.json()
    assert reports["customers"]["loaded"] == 97 and reports["customers"]["skipped"] == 5
    assert reports["customers"]["duplicate_ids"] == ["U050"]
    assert reports["chats"]["fixes"]["ids_matched_ignoring_case"] == 4 and "U999" in reports["chats"]["orphan_ids"]
    apps = reports["installed_apps"]
    assert apps["skipped"] == 39 and "Jat" not in json.dumps(apps["preview"])

    built = c.post("/api/brains/build", json={}).json()
    assert built["built"] == 96 and built["failed"] == []
    decided = c.post("/api/decide/all", json={}).json()
    assert decided["failed"] == [] and decided["decided"] == 96

    key = json.loads((DATA / "personas_answer_key.json").read_text())
    for u in c.get("/api/customers").json():
        p, d = key[u["customer_id"]], u["decision"]
        if p in {"money_stress", "gamer"} and d["action"] == "contact":
            assert d["tone"] not in PAID, (u["customer_id"], d)
        if p == "opted_out":
            assert d["action"] == "hold", (u["customer_id"], d)
