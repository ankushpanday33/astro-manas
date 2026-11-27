"""Brain builder: one living brain per user of the AI astrology app.

  chart    - the stored "user" row from the Vedic Astrology Engine (numerology + birth Panchang), computed once
  world    - the user's graph: chart, sessions, chats, purchases, messages
  memory   - what they said in chats, read in time
  facts    - chart facts read from the row + behaviour facts computed in code, each citing its source
  beliefs  - engagement, purchase intent, topic, anxiety, reachability; judged when Claude is on
  persona  - the twin's portrait (MiroFish-style agent profile), built from chart + behaviour
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .. import llm, privacy, store
from ..astro import engine
from ..packs import get_pack
from . import beliefs as beliefs_mod
from . import memory as memory_mod
from .facts import _d, astro_facts

CHART_KEYS = ["radical_number", "radical_planet", "destiny_number", "destiny_planet", "name_number", "name_planet",
              "lucky_numbers", "challenging_numbers", "lucky_colours_primary", "traditional_gemstones", "gemstone_prescription",
              "loshu_grid", "loshu_missing_digits", "nakshatra_name", "nakshatra_lord", "nakshatra_pada", "tithi_name",
              "vara_name", "vara_lord", "yoga_name", "karana_name", "overall_profile_score", "personality_title",
              "birth_time_confidence", "panchang_uncertain_angas", "rule_version"]


def _world(records: dict[str, list[dict]], pack: dict[str, Any], uid: str, row: dict[str, Any] | None) -> dict[str, Any]:
    nodes, edges, counts = [], [], {}
    me = f"Customer:{uid}"
    nodes.append({"id": me, "type": "Customer", "label": privacy.alias(uid)})
    if row:
        counts["AstroRow"] = 1
        nodes.append({"id": f"AstroRow:{uid}", "type": "AstroRow", "label": "user row"})
        edges.append({"from": f"AstroRow:{uid}", "to": me, "type": "computed_for"})
    src_to_type = {spec["source"]: name for name, spec in pack["objects"].items()}
    for src, rows in records.items():
        otype = src_to_type.get(src)
        if not otype or otype in {"User", "AstroRow"}:
            continue
        counts[otype] = len(rows)
        link = next((l for l in pack["links"] if l["from"] == otype), None)
        for r in rows:
            nodes.append({"id": f"{otype}:{r['_row_id']}", "type": otype, "label": r["_row_id"]})
            edges.append({"from": f"{otype}:{r['_row_id']}", "to": me, "type": link["type"] if link else "related_to"})
    return {"nodes": nodes, "edges": edges, "counts": counts, "summary": f"{len(counts) + 1} object types, {len(edges)} links"}


def _texts(records: dict[str, list[dict]]) -> list[dict[str, Any]]:
    texts = [{"text": c["text"], "written_on": _d(c.get("at")) or date.today(), "ref": {"source": "chats", "row_id": c["_row_id"]}}
             for c in records.get("chats", []) if c.get("text")]
    texts += [{"text": c["reply_text"], "written_on": _d(c.get("sent_at")) or date.today(), "ref": {"source": "communications", "row_id": c["_row_id"]}}
              for c in records.get("communications", []) if c.get("direction") == "in" and c.get("reply_text")]
    return texts


def _persona(profile: dict[str, Any], fv: dict[str, Any], beliefs: list[dict[str, Any]], row: dict[str, Any] | None) -> dict[str, Any]:
    b = {x["id"]: x for x in beliefs}
    traits = []
    if row:
        traits.append(f"Radical {row['radical_number']} ({row['radical_planet'].title()})")
        if row.get("nakshatra_name"):
            traits.append(f"{row['nakshatra_name']} Nakshatra: {', '.join(row['nakshatra_tags']).lower()}")
    if fv.get("main_topic"):
        traits.append(f"thinking about {fv['main_topic']}")
    if fv.get("anxiety_flag"):
        traits.append("sounds anxious lately")
    if fv.get("upcoming_event"):
        traits.append(f"has {fv['upcoming_event']}")
    if (fv.get("usage_trend") or 0) < -0.4:
        traits.append("drifting away from the app")
    if fv.get("app_interests"):
        traits.append("apps point to " + ", ".join(fv["app_interests"][:3]).lower())
    eng = b.get("engagement", {}).get("value")
    persona = {
        "alias": privacy.alias(profile["customer_id"]),
        "language": profile.get("preferred_language") or "English",
        "city": profile.get("city"),
        "responds_on": fv.get("best_responding_slot"),
        "active_window": fv.get("active_window"),
        "stated_time": fv.get("stated_time_preference"),
        "traits": traits,
        "mood": "anxious" if fv.get("anxiety_flag") else "guarded" if fv.get("contact_objection_flag") else "devoted" if eng == "high" else "drifting" if eng == "low" else "curious",
        "method": "rules",
    }
    persona["narrative"] = (
        f"Speaks {persona['language']}, from {persona['city']}. "
        + (f"Chart: {row['personality_title']}. " if row else "No chart yet: birth-data consent missing. ")
        + (f"Usually in the app in the {persona['active_window']}. " if persona["active_window"] else "")
        + (f"Responds best on {persona['responds_on']}. " if persona["responds_on"] else "")
        + (("Tends to: " + "; ".join(traits[1 if row else 0:]) + ".") if traits[1 if row else 0:] else "")
    ).strip()
    if llm.enabled():
        digest = {"chart": {k: row.get(k) for k in CHART_KEYS} if row else None,
                  "facts": {k: v for k, v in fv.items() if v is not None}, "beliefs": {x["id"]: x["value"] for x in beliefs}}
        out = llm.ask_json(
            "Write a short, respectful persona of an astrology-app user for a simulation agent, grounded only in the data given. "
            "Never invent chart values. Describe them in third person.",
            f"User {persona['alias']}.\n{privacy.pseudonymise(digest, [profile.get('name', '')])}",
            {"type": "object", "properties": {"narrative": {"type": "string"}, "communication_style": {"type": "string"},
                                              "what_motivates_them": {"type": "string"}, "what_to_avoid": {"type": "string"}}},
            max_tokens=800)
        if out:
            persona.update(out)
            persona["method"] = "llm"
    return persona


def build_brain(customer_id: str, pack_id: str, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    pack = get_pack(pack_id)
    records = store.records_for(customer_id)
    profile = (records.get("customers") or [{"customer_id": customer_id}])[0]

    # Engine first (PRD 5.5): compute once, store on the user row; everything below reads the row.
    row = engine.get_user_row(customer_id) if profile.get("astro_consent_at") else None
    # PRD 5.5 recompute triggers: a config version bump, or any birth input changed since the row was computed.
    changed = row and (row.get("dob") != profile.get("dob") or (row.get("birth_time") or None) != (profile.get("birth_time") or None)
                       or str(row.get("birth_latitude")) != str(float(profile["birth_latitude"]) if profile.get("birth_latitude") not in (None, "") else None)
                       or (profile.get("numerology_name") and row.get("numerology_name") != profile.get("numerology_name")))
    if profile.get("astro_consent_at") and (not row or row.get("rule_version") != engine.C.RULE_VERSION or changed):
        row = engine.compute_and_store(profile)

    world = _world(records, pack, customer_id, row)
    memory = memory_mod.read_texts(_texts(records), [profile.get("name", "")])
    facts, stats, predictions = astro_facts(records, pack, today, memory, row)
    predictions.pop("rows", None)
    fv = {f["id"]: f["value"] for f in facts}
    beliefs = beliefs_mod.BELIEF_BUILDERS[pack_id](fv, stats, pack)
    beliefs = beliefs_mod.judge(beliefs, {f["id"]: f for f in facts})
    persona = _persona(profile, fv, beliefs, row)

    brain = {
        "customer_id": customer_id, "alias": privacy.alias(customer_id), "display_name": profile.get("name") or customer_id,
        "pack": pack_id, "built_at": datetime.now().isoformat(timespec="seconds"), "as_of": today.isoformat(),
        "profile": {k: profile.get(k) for k in pack["objects"]["User"]["fields"]},
        "chart": {k: row.get(k) for k in CHART_KEYS} if row else None,
        "world": world, "memory": memory, "facts": facts,
        "comm_stats": {ch: {w: {k: v for k, v in c.items() if k != "rows"} for w, c in ws.items()} for ch, ws in stats.items()},
        "beliefs": beliefs, "persona": persona, "predictions": predictions, "llm": llm.status(),
    }
    store.save_brain(customer_id, pack_id, brain["built_at"], brain)
    return brain
