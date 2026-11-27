"""Versioned config for the Vedic Astrology Engine (PRD Draft 2.0). Tables are config, not code paths.

Bump RULE_VERSION / COMPATIBILITY_VERSION when any table changes; rows keep the version they were computed with.
"""
from __future__ import annotations

RULE_VERSION = "1.0"
COMPATIBILITY_VERSION = "1.0"
SOURCE_TRADITION = "INDIAN_V1"
LOSHU_VARIANT = "DOB_ONLY"  # or "AUGMENTED"; never mixed (PRD 3.12)

# 3.5 Chaldean letter map (9 is sacred: no letter)
CHALDEAN = {
    "A": 1, "I": 1, "J": 1, "Q": 1, "Y": 1, "B": 2, "K": 2, "R": 2,
    "C": 3, "G": 3, "L": 3, "S": 3, "D": 4, "M": 4, "T": 4,
    "E": 5, "H": 5, "N": 5, "X": 5, "U": 6, "V": 6, "W": 6,
    "O": 7, "Z": 7, "F": 8, "P": 8,
}

# 3.6 Number to planet
PLANET = {1: "SUN", 2: "MOON", 3: "JUPITER", 4: "RAHU", 5: "MERCURY", 6: "VENUS", 7: "KETU", 8: "SATURN", 9: "MARS"}
PLANET_NAME = {"SUN": "Surya", "MOON": "Chandra", "JUPITER": "Guru", "RAHU": "Rahu", "MERCURY": "Budh",
               "VENUS": "Shukra", "KETU": "Ketu", "SATURN": "Shani", "MARS": "Mangal"}

# 3.7 Compatibility table v1.0
FRIENDLY = {1: {1, 2, 3, 9}, 2: {1, 2, 3, 5}, 3: {1, 2, 3, 5, 6, 8, 9}, 4: {1, 5, 6, 7}, 5: {1, 2, 3, 5, 6},
            6: {1, 3, 4, 5, 6, 8, 9}, 7: {1, 4, 5, 6}, 8: {3, 5, 6, 8}, 9: {1, 2, 3, 5, 6, 9}}
CHALLENGING = {1: {6, 8}, 2: {4, 8, 9}, 3: {4, 7}, 4: {2, 8, 9}, 5: {4, 8, 9}, 6: {2, 7}, 7: {2, 3, 8, 9},
               8: {1, 2, 4, 7}, 9: {4, 7, 8}}

# 3.10 Colours, metals, traditional gemstones
COLOURS = {1: ["Red", "Orange", "Golden"], 2: ["White", "Cream"], 3: ["Yellow", "Golden yellow"],
           4: ["Grey", "Smoky", "Blue-black"], 5: ["Green"], 6: ["White", "Pink", "Pastel"],
           7: ["Grey", "Smoky shades"], 8: ["Black", "Dark blue"], 9: ["Red", "Coral"]}
METALS = {1: ["Gold", "Copper"], 2: ["Silver"], 3: ["Gold"], 4: ["Lead (traditional)"], 5: ["Bronze", "Brass"],
          6: ["Silver"], 7: ["Mixed metals"], 8: ["Iron"], 9: ["Copper"]}
STONE = {1: "Ruby", 2: "Pearl", 3: "Yellow Sapphire", 4: "Hessonite", 5: "Emerald", 6: "Diamond / White Sapphire",
         7: "Cat's Eye", 8: "Blue Sapphire", 9: "Red Coral"}

# 3.12 Lo Shu planes
PLANES = {
    "ROW_TOP_4_9_2": (4, 9, 2), "ROW_MID_3_5_7": (3, 5, 7), "ROW_BOT_8_1_6": (8, 1, 6),
    "COL_LEFT_4_3_8": (4, 3, 8), "COL_MID_9_5_1": (9, 5, 1), "COL_RIGHT_2_7_6": (2, 7, 6),
    "DIAG_4_5_6": (4, 5, 6), "DIAG_2_5_8": (2, 5, 8),
}

# 4.2 Tithi themes (index 1..15 within a paksha; 15 = Purnima, 30 = Amavasya)
TITHI_NAMES = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami",
               "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi"]
TITHI_THEMES = {
    "Pratipada": ["Initiative", "Independence"], "Dwitiya": ["Cooperation", "Relationships"],
    "Tritiya": ["Courage", "Creativity"], "Chaturthi": ["Determination", "Problem-solving"],
    "Panchami": ["Learning", "Curiosity"], "Shashthi": ["Discipline", "Competition"],
    "Saptami": ["Confidence", "Leadership"], "Ashtami": ["Intensity", "Resilience"],
    "Navami": ["Courage", "Action"], "Dashami": ["Responsibility", "Achievement"],
    "Ekadashi": ["Self-control", "Introspection"], "Dwadashi": ["Service", "Generosity"],
    "Trayodashi": ["Adaptability", "Refinement"], "Chaturdashi": ["Strong will", "Intensity"],
    "Purnima": ["Expressiveness", "Emotional visibility"], "Amavasya": ["Introspection", "Inward focus"],
}

# 4.3 Vara (Python weekday(): Monday = 0)
VARA = [("Monday", "Somvar", "MOON", ["Sensitivity", "Empathy", "Imagination"]),
        ("Tuesday", "Mangalvar", "MARS", ["Courage", "Action", "Competitiveness"]),
        ("Wednesday", "Budhvar", "MERCURY", ["Communication", "Logic", "Adaptability"]),
        ("Thursday", "Guruvar", "JUPITER", ["Wisdom", "Teaching", "Optimism"]),
        ("Friday", "Shukravar", "VENUS", ["Creativity", "Aesthetics", "Harmony"]),
        ("Saturday", "Shanivar", "SATURN", ["Discipline", "Patience", "Responsibility"]),
        ("Sunday", "Ravivar", "SUN", ["Leadership", "Confidence", "Independence"])]

# 4.4 Nakshatras and Vimshottari lords
VIMSHOTTARI = ["KETU", "VENUS", "SUN", "MOON", "MARS", "RAHU", "JUPITER", "SATURN", "MERCURY"]
NAKSHATRAS = [
    ("Ashwini", ["Quick", "Energetic"]), ("Bharani", ["Determination", "Responsibility"]),
    ("Krittika", ["Directness", "Discernment"]), ("Rohini", ["Creativity", "Attraction"]),
    ("Mrigashira", ["Curiosity", "Exploration"]), ("Ardra", ["Analytical", "Transformative"]),
    ("Punarvasu", ["Optimism", "Renewal"]), ("Pushya", ["Nurturing", "Discipline"]),
    ("Ashlesha", ["Strategic", "Observant"]), ("Magha", ["Tradition", "Authority"]),
    ("Purva Phalguni", ["Creativity", "Enjoyment"]), ("Uttara Phalguni", ["Commitment", "Cooperation"]),
    ("Hasta", ["Skill", "Communication"]), ("Chitra", ["Design", "Ambition"]),
    ("Swati", ["Independence", "Adaptability"]), ("Vishakha", ["Goal-oriented", "Persistent"]),
    ("Anuradha", ["Friendship", "Devotion"]), ("Jyeshtha", ["Responsibility", "Leadership"]),
    ("Moola", ["Research", "Root-cause thinking"]), ("Purva Ashadha", ["Confidence", "Conviction"]),
    ("Uttara Ashadha", ["Perseverance", "Integrity"]), ("Shravana", ["Listening", "Learning"]),
    ("Dhanishta", ["Rhythm", "Teamwork"]), ("Shatabhisha", ["Research", "Independence"]),
    ("Purva Bhadrapada", ["Intensity", "Idealism"]), ("Uttara Bhadrapada", ["Patience", "Depth"]),
    ("Revati", ["Compassion", "Guidance"]),
]
SIGNS = ["ARIES", "TAURUS", "GEMINI", "CANCER", "LEO", "VIRGO", "LIBRA", "SCORPIO", "SAGITTARIUS",
         "CAPRICORN", "AQUARIUS", "PISCES"]

# 4.5 Yoga
YOGAS = [("Vishkambha", "Determination"), ("Priti", "Affection, bonding"), ("Ayushman", "Vitality, endurance"),
         ("Saubhagya", "Optimism, opportunity"), ("Shobhana", "Beauty, creativity"), ("Atiganda", "Intensity, obstacles"),
         ("Sukarma", "Constructive action"), ("Dhriti", "Stability, patience"), ("Shoola", "Strong opinions"),
         ("Ganda", "Complexity, resilience"), ("Vriddhi", "Growth, ambition"), ("Dhruva", "Stability, consistency"),
         ("Vyaghata", "Assertiveness"), ("Harshana", "Enthusiasm"), ("Vajra", "Determination"),
         ("Siddhi", "Accomplishment"), ("Vyatipata", "Unconventional thinking"), ("Variyana", "Comfort, refinement"),
         ("Parigha", "Persistence"), ("Shiva", "Harmony, discipline"), ("Siddha", "Skill, capability"),
         ("Sadhya", "Learning, achievement"), ("Shubha", "Positive outlook"), ("Shukla", "Clarity, expression"),
         ("Brahma", "Knowledge, wisdom"), ("Indra", "Leadership, influence"), ("Vaidhriti", "Strong will, intensity")]

# 4.6 Karana
MOVABLE_KARANA = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]
KARANA_THEMES = {
    "Bava": ["Initiative", "Activity"], "Balava": ["Learning", "Growth"], "Kaulava": ["Cooperation", "Social interaction"],
    "Taitila": ["Organisation", "Planning"], "Gara": ["Practicality", "Execution"], "Vanija": ["Business", "Negotiation"],
    "Vishti": ["Persistence", "Intensity"], "Shakuni": ["Observation", "Strategy"],
    "Chatushpada": ["Practicality", "Steadiness"], "Naga": ["Depth", "Resilience"], "Kimstughna": ["Service", "Completion"],
}

# 4.7 Weights (config, stored on every row)
PANCHANG_WEIGHTS = {"nakshatra": 0.30, "tithi": 0.20, "yoga": 0.20, "vara": 0.15, "karana": 0.15}

# Anga score rule v1 (placeholder for the astrology team): description strength starts at 80,
# +10 when birth sits well inside the Anga (not within 10% of either boundary), -15 when the Anga is uncertain
# inside the approximate birth-time window. Not a measure of intelligence, success or character.
ANGA_SCORE_BASE, ANGA_SCORE_CLEAR, ANGA_SCORE_UNCERTAIN = 80, 10, -15

# Responsible copy (PRD 2): words that must never appear in a user-facing message.
BANNED_COPY = ["guarantee", "guaranteed", "evil number", "cure", "100%", "definitely will", "bad luck", "curse",
               "loan", "debt", "betting", "jackpot", "cheat", "affair", "pregnan", "caste"]
