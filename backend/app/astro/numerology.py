"""Module A: Numerology Engine, exactly as the PRD (section 3). Every number keeps compound, root, planet and proof."""
from __future__ import annotations

from datetime import date
from typing import Any

from . import config as C


def reduce_number(n: int) -> int:
    while n > 9:
        n = sum(int(x) for x in str(n))
    return n


def _reduction_steps(total: int) -> str:
    steps, n = [str(total)], total
    while n > 9:
        n = sum(int(x) for x in str(n))
        steps.append(str(n))
    return " = ".join(steps)


def radical(day: int) -> dict[str, Any]:
    value = ((day - 1) % 9) + 1
    d = f"{day:02d}"
    s = int(d[0]) + int(d[1])
    calc = f"{d[0]}+{d[1]} = {s}" + (f" = {reduce_number(s)}" if s > 9 else "")
    return {"value": value, "compound": day, "planet": C.PLANET[value], "calculation": calc}


def destiny(dob: date) -> dict[str, Any]:
    digits = dob.strftime("%d%m%Y")
    total = sum(int(x) for x in digits)
    return {"value": reduce_number(total), "compound": total, "planet": C.PLANET[reduce_number(total)],
            "calculation": f"{'+'.join(digits)} = {_reduction_steps(total)}"}


def name_number(name: str) -> dict[str, Any]:
    letters = [c for c in name.upper() if c.isalpha()]
    vals = [C.CHALDEAN.get(c, 0) for c in letters]
    total = sum(vals)
    clean = "".join(letters)
    return {"value": reduce_number(total) if total else None, "compound": total,
            "planet": C.PLANET.get(reduce_number(total)) if total else None,
            "calculation": f"{clean} = {'+'.join(map(str, vals))} = {_reduction_steps(total)}"}


def scores(r: int, d: int, n: int | None) -> dict[int, int]:
    out = {}
    for c in range(1, 10):
        s = 0
        for base, w in ((r, 2), (d, 2), (n, 1)):
            if base is None:
                continue
            if c in C.FRIENDLY[base]:
                s += w
            elif c in C.CHALLENGING[base]:
                s -= w
        out[c] = s
    return out


def lo_shu(dob: date, r: int, d: int, variant: str = C.LOSHU_VARIANT) -> dict[str, Any]:
    digits = [int(x) for x in dob.strftime("%d%m%Y") if x != "0"]
    if variant == "AUGMENTED":
        digits += [r, d]
    counts = {str(k): digits.count(k) for k in range(1, 10) if k in digits}
    missing = [k for k in range(1, 10) if k not in digits]
    planes = [k for k, v in C.PLANES.items() if all(x in digits for x in v)]
    return {"variant": variant, "counts": counts, "missing": missing, "complete_planes": planes}


def compute(dob: date, numerology_name: str) -> dict[str, Any]:
    """Returns flat columns (groups B, C, D) plus the numerology_report snapshot (PRD 3.13)."""
    r, d, n = radical(dob.day), destiny(dob), name_number(numerology_name or "")
    sc = scores(r["value"], d["value"], n["value"])
    top = max(sc.values())
    lucky = [k for k, v in sc.items() if v == top and v > 0]
    neutral = [k for k, v in sc.items() if v == 0]
    challenging = [k for k, _ in sorted(((k, v) for k, v in sc.items() if v < 0), key=lambda kv: (kv[1], kv[0]))]
    common = sorted(C.CHALLENGING[r["value"]] & C.CHALLENGING[d["value"]])
    primary = C.COLOURS[r["value"]]
    secondary = [c for c in C.COLOURS[d["value"]] if c not in primary]
    metals = list(dict.fromkeys(C.METALS[r["value"]] + C.METALS[d["value"]]))
    ls = lo_shu(dob, r["value"], d["value"])

    flat = {
        "radical_number": r["value"], "radical_compound": r["compound"], "radical_planet": r["planet"], "radical_calculation": r["calculation"],
        "destiny_number": d["value"], "destiny_compound": d["compound"], "destiny_planet": d["planet"], "destiny_calculation": d["calculation"],
        "name_number": n["value"], "name_compound": n["compound"], "name_planet": n["planet"], "name_calculation": n["calculation"],
        "number_scores": {str(k): v for k, v in sc.items()},
        "lucky_numbers": lucky, "neutral_numbers": neutral, "challenging_numbers": challenging,
        "common_challenging_numbers": common,
        "lucky_colours_primary": primary, "lucky_colours_secondary": secondary, "lucky_metals": metals,
        "traditional_gemstones": [C.STONE[r["value"]]], "gemstone_prescription": "REQUIRES_KUNDLI_REVIEW",
        "loshu_variant": ls["variant"], "loshu_grid": ls["counts"], "loshu_missing_digits": ls["missing"],
        "loshu_complete_planes": ls["complete_planes"],
        "dob_method": "INDIAN_NUMEROLOGY", "name_method": "CHALDEAN", "compatibility_version": C.COMPATIBILITY_VERSION,
    }
    flat["numerology_report"] = {
        "system": {"dob_method": "INDIAN_NUMEROLOGY", "name_method": "CHALDEAN", "compatibility_version": C.COMPATIBILITY_VERSION},
        "numbers": {"radical_number": {k: r[k] for k in ("value", "compound", "planet")},
                    "destiny_number": {k: d[k] for k in ("value", "compound", "planet")},
                    "name_number": {k: n[k] for k in ("value", "compound", "planet")}},
        "compatibility": {"lucky_numbers": lucky, "neutral_numbers": neutral, "challenging_numbers": challenging,
                          "common_challenging_numbers": common},
        "recommendations": {"primary_colour": primary, "secondary_colours": secondary, "lucky_metals": metals,
                            "traditional_gemstones": [C.STONE[r["value"]]], "gemstone_prescription": "REQUIRES_KUNDLI_REVIEW"},
        "lo_shu": ls,
        "explanation": {"radical_calculation": r["calculation"], "destiny_calculation": d["calculation"],
                        "name_calculation": n["calculation"], "compatibility_method": "WEIGHTED_PLANETARY_FRIENDSHIP"},
    }
    return flat


def name_trial(spelling: str) -> dict[str, Any]:
    n = name_number(spelling)
    return {"name": "".join(c for c in spelling.upper() if c.isalpha()), "compound": n["compound"], "value": n["value"],
            "planet": n["planet"], "calculation": n["calculation"]}
