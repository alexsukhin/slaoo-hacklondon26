from typing import List, Dict, Any


IMPROVEMENT_KEYWORDS = {
    "solar": ["solar", "photovoltaic", "pv panel", "solar panel"],
    "insulation": ["insulation", "wall insulation", "external wall", "cavity wall"],
    "windows": ["window", "double glaz", "triple glaz", "glazing"],
    "heat_pump": ["heat pump", "air source", "ground source", "ashp", "gshp"]
}


def filter_by_improvement_type(
    applications: List[Dict[str, Any]], 
    improvement_type: str
) -> List[Dict[str, Any]]:
    """
    Filter planning applications by improvement type using keyword matching.
    
    TODO: Improve beyond simple string matching:
    - Use fuzzy matching
    - Use embeddings/semantic search
    - Check document metadata for better classification
    """
    keywords = IMPROVEMENT_KEYWORDS.get(improvement_type.lower(), [improvement_type])
    matching = []
    
    for app in applications:
        proposal = app.get("proposal", "").lower()
        if any(keyword in proposal for keyword in keywords):
            matching.append(app)
    
    return matching
