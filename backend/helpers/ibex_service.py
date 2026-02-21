from datetime import datetime, timedelta
from typing import List, Dict, Any
from ibex_client import IBexClient


async def fetch_planning_applications(
    ibex_client: IBexClient,
    latitude: float,
    longitude: float,
    radius: int = 500,
    years_back: int = 3
) -> List[Dict[str, Any]]:
    """Fetch approved planning applications from IBex API"""
    
    date_to = datetime.now().date().isoformat()
    date_from = (datetime.now().date() - timedelta(days=years_back * 365)).isoformat()
    
    print(f"🔍 Searching for retrofit examples in {radius}m radius...")
    
    applications = await ibex_client.search_by_location(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        date_from=date_from,
        date_to=date_to,
        filters={
            "normalised_decision": ["Approved"],
            "normalised_application_type": ["full planning application", "householder planning application"]
        }
    )
    
    if not isinstance(applications, list):
        applications = []
    
    print(f"Found {len(applications)} approved applications\n")
    
    return applications
