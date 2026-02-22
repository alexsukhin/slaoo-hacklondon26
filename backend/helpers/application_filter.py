from typing import List, Dict, Any
import re
from thefuzz import fuzz

IMPROVEMENT_KEYWORDS = {
    "solar": [
        "solar", "photovoltaic", "pv", "pv panel",
        "solar panel", "solar pv", "photovoltaics"
    ],

    "insulation": [
        "insulation", "wall insulation", "external wall",
        "cavity wall", "loft insulation", "roof insulation"
    ],

    "windows": [
        "window", "windows", "double glazing",
        "triple glazing", "glazing", "u-value",
        "energy efficient windows"
    ],

    "heat_pump": [
        "heat pump", "air source", "ground source",
        "ashp", "gshp",
        "air source heat pump",
        "ground source heat pump"
    ],

    "battery": [
        "battery storage", "home battery",
        "powerwall", "battery unit",
        "energy storage system",
        "tesla battery"
    ],

    "loft_conversion": [
        "loft conversion", "roof extension",
        "dormer", "mansard",
        "roof enlargement", "attic conversion"
    ],

    "cladding": [
        "external cladding", "render",
        "external wall finish",
        "facade upgrade", "wall rendering",
        "external insulation system"
    ],

    "ev_charger": [
        "electric vehicle charger",
        "ev charger",
        "charging point",
        "vehicle charging",
        "car charging point",
        "ev installation"
    ]
}

def normalize_text(text: str) -> str:
    """
    Lowercase and remove punctuation for consistent matching.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def filter_by_improvement_type(
    applications: List[Dict[str, Any]], 
    improvement_type: str,
    use_fuzzy: bool = True,
    fuzzy_threshold: int = 85
) -> List[Dict[str, Any]]:
    """
    Filter planning applications by improvement type using:
    1. Normalized keyword matching
    2. Optional fuzzy string matching for typos/variations
    """
    keywords = [normalize_text(k) for k in IMPROVEMENT_KEYWORDS.get(improvement_type.lower(), [improvement_type.lower()])]
    matching = []

    for app in applications:
        proposal = normalize_text(app.get("proposal", ""))
        found = False

        for keyword in keywords:
            if keyword in proposal:
                matching.append(app)
                found = True
                break
        if found:
            continue

        if use_fuzzy:
            for keyword in keywords:
                score = fuzz.partial_ratio(keyword, proposal)
                if score >= fuzzy_threshold:
                    matching.append(app)
                    break

    return matching