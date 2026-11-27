"""Upload test-data/hard-100 through the real API and print each upload report.

  python scripts/upload_hard_dataset.py              # in-process, on a throwaway database
  python scripts/upload_hard_dataset.py --live       # against the running server on http://127.0.0.1:8010 (replaces its data)
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "test-data" / "hard-100"
FILES = [("customers", "1_users.csv"), ("sessions", "2_sessions.ndjson"), ("chats", "3_chats.csv"), ("purchases", "4_purchases.json"),
         ("communications", "5_messages.tsv"), ("events", "6_events.xlsx"), ("installed_apps", "7_installed_apps.csv")]


def client():
    if "--live" in sys.argv:
        import httpx

        return httpx.Client(base_url="http://127.0.0.1:8010", timeout=300)
    os.environ["MANAS_DB"] = os.path.join(tempfile.mkdtemp(), "hard.db")
    os.environ["MANAS_LLM"] = "0"
    sys.path.insert(0, str(ROOT / "backend"))
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


def main() -> None:
    c = client()
    c.post("/api/data/reset", json={"confirm": True})
    for source, name in FILES:
        r = c.post(f"/api/ingest/{source}", files={"file": (name, (DATA / name).read_bytes())}, data={"mode": "append", "pack": "astro_engagement"})
        body = r.json()
        if r.status_code != 200:
            print(f"\n{name}: ERROR {r.status_code} {body}")
            continue
        reasons = Counter(x["reason"].split(":")[0] if "dob" not in x["reason"] else x["reason"] for x in body["skipped_rows"])
        print(f"\n{name} -> {source}: {body['loaded']} loaded, {body['skipped']} skipped of {body['rows_in_file']}")
        print("  mapped:", body["column_mapping"])
        if body.get("orphan_rows"):
            print("  rows with no matching user:", body["orphan_rows"], body.get("orphan_ids"))
        if body.get("duplicate_ids"):
            print("  duplicate ids in file (last row wins):", body["duplicate_ids"])
        if body.get("fixes"):
            print("  fixes:", body["fixes"])
        for reason, n in reasons.most_common(8):
            print(f"  skipped x{n}: {reason}")
    b = c.post("/api/brains/build", json={}).json()
    d = c.post("/api/decide/all", json={}).json()
    print("\nbuild:", b.get("built"), "| decide:", d)
    users = c.get("/api/customers").json()
    charts = sum(1 for u in users if u["headline"]["radical"])
    panchang = sum(1 for u in users if u["headline"]["nakshatra"])
    print(f"users {len(users)} | charts {charts} | panchang {panchang}")
    key = json.loads((DATA / "personas_answer_key.json").read_text())
    by = {}
    for u in users:
        dd = u["decision"]
        by.setdefault(key.get(u["customer_id"], "?"), Counter())[f"{dd['action']}:{dd['tone']}"] += 1
    for p, cnt in sorted(by.items()):
        print(f"  {p:15s} {cnt.most_common(3)}")


if __name__ == "__main__":
    main()
