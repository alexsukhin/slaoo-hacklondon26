from datetime import datetime
from typing import List, Dict, Any, Optional
from models import RetrofitExample
import re

def calculate_average_approval_time(applications: List[Dict[str, Any]]) -> Optional[float]:
    """Calculate average time from application to decision in days"""
    decision_times = []
    
    for app in applications:
        if app.get("application_date") and app.get("decided_date"):
            try:
                app_date = datetime.fromisoformat(app["application_date"].replace('Z', '+00:00'))
                dec_date = datetime.fromisoformat(app["decided_date"].replace('Z', '+00:00'))
                days = (dec_date - app_date).days
                decision_times.append(days)
            except:
                pass
    
    return sum(decision_times) / len(decision_times) if decision_times else None


def extract_examples(applications: List[Dict[str, Any]], property_metrics: Dict[str, Any], limit: int = 5) -> List[RetrofitExample]:
    examples = []
    current_epc = property_metrics.get("current_energy_rating", "D")

    for app in applications[:limit]:
        decision_time = None

        if app.get("application_date") and app.get("decided_date"):
            try:
                app_date = datetime.fromisoformat(app["application_date"].replace('Z', '+00:00'))
                dec_date = datetime.fromisoformat(app["decided_date"].replace('Z', '+00:00'))
                decision_time = (dec_date - app_date).days
            except:
                pass

        # 🔥 Extract coordinates from centre_point
        latitude = None
        longitude = None

        centre = app.get("centre_point")
        if centre:
            match = re.search(r"POINT\(([-\d\.]+)\s+([-\d\.]+)\)", centre)
            if match:
                longitude = float(match.group(1))
                latitude = float(match.group(2))

        examples.append(RetrofitExample(
            planning_reference=app.get("planning_reference", "N/A"),
            proposal=app.get("proposal", "N/A"),
            decision=app.get("normalised_decision", "N/A"),
            decision_time_days=decision_time,
            application_date=app.get("application_date", "N/A"),
            decided_date=app.get("decided_date"),
            latitude=latitude,
            longitude=longitude,
            current_energy_rating=app.get("current_energy_rating", current_epc)
        ))

    return examples
