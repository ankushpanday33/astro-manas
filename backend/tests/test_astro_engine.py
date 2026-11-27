"""QA fixture from PRD 5.6: RAVI, 24/06/2000. Every value below is copied from the PRD's worked example row."""
from datetime import date, time

from app.astro import numerology, panchang


def test_prd_worked_example_ravi():
    r = numerology.compute(date(2000, 6, 24), "RAVI")
    assert (r["radical_number"], r["radical_compound"], r["radical_planet"]) == (6, 24, "VENUS")
    assert r["radical_calculation"] == "2+4 = 6"
    assert (r["destiny_number"], r["destiny_compound"], r["destiny_planet"]) == (5, 14, "MERCURY")
    assert r["destiny_calculation"] == "2+4+0+6+2+0+0+0 = 14 = 5"
    assert (r["name_number"], r["name_compound"], r["name_planet"]) == (1, 10, "SUN")
    assert r["name_calculation"] == "RAVI = 2+1+6+1 = 10 = 1"
    assert r["number_scores"] == {"1": 5, "2": 1, "3": 5, "4": 0, "5": 4, "6": 3, "7": -2, "8": -1, "9": 1}
    assert r["lucky_numbers"] == [1, 3]
    assert r["neutral_numbers"] == [4]
    assert r["challenging_numbers"] == [7, 8]
    assert r["common_challenging_numbers"] == []
    assert r["lucky_colours_primary"] == ["White", "Pink", "Pastel"]
    assert r["lucky_colours_secondary"] == ["Green"]
    assert r["lucky_metals"] == ["Silver", "Bronze", "Brass"]
    assert r["traditional_gemstones"] == ["Diamond / White Sapphire"]
    assert r["gemstone_prescription"] == "REQUIRES_KUNDLI_REVIEW"
    assert r["loshu_grid"] == {"2": 2, "4": 1, "6": 1}
    assert r["loshu_missing_digits"] == [1, 3, 5, 7, 8, 9]
    assert r["loshu_complete_planes"] == []


def test_radical_table_and_augmented_loshu():
    assert [numerology.radical(d)["value"] for d in (5, 14, 19, 24, 29, 31)] == [5, 5, 1, 6, 2, 4]
    aug = numerology.lo_shu(date(2000, 6, 24), 6, 5, "AUGMENTED")
    assert "DIAG_4_5_6" in aug["complete_planes"]


def test_karana_fixed_and_movable():
    assert panchang.karana_name(0) == ("Kimstughna", "FIXED")
    assert panchang.karana_name(1) == ("Bava", "MOVABLE")
    assert panchang.karana_name(7) == ("Vishti", "MOVABLE")
    assert panchang.karana_name(57)[0] == "Shakuni" and panchang.karana_name(59)[0] == "Naga"


def test_panchang_rules():
    assert panchang.compute(date(2000, 6, 24), None, "UNKNOWN", None, 26.8467, 80.9462, "Asia/Kolkata") is None
    p = panchang.compute(date(2000, 6, 24), time(10, 35), "EXACT", None, 26.8467, 80.9462, "Asia/Kolkata")
    assert p["birth_datetime_utc"].startswith("2000-06-24T05:05")
    assert p["vara_name"] == "Saturday" and p["vara_sunrise_adjusted"] is False
    assert 1 <= p["nakshatra_pada"] <= 4 and 1 <= p["tithi_index"] <= 30
    assert p["tithi_start_utc"] <= p["birth_datetime_utc"] <= p["tithi_end_utc"]
    # Born before sunrise: the Vedic day is still the previous weekday.
    early = panchang.compute(date(2000, 6, 24), time(4, 0), "EXACT", None, 26.8467, 80.9462, "Asia/Kolkata")
    assert early["vara_sunrise_adjusted"] is True and early["vara_name"] == "Friday"
    approx = panchang.compute(date(2000, 6, 24), time(10, 35), "APPROXIMATE", 600, 26.8467, 80.9462, "Asia/Kolkata")
    assert approx["panchang_uncertain_angas"]


def test_user_table_groups_match_prd():
    from app.astro.engine import GROUPS
    assert GROUPS["F"][0] == "tithi_index" and GROUPS["F"][-1] == "panchang_uncertain_angas"
    assert GROUPS["G"][-1] == "panchang_score_weights" and "overall_profile_score" in GROUPS["G"]
    assert GROUPS["H"][0] == "personality_title" and GROUPS["H"][-1] == "ai_report_generated_at"
    assert GROUPS["I"][0] == "numerology_report"
