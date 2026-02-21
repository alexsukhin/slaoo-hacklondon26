import httpx
import os
import base64
from typing import Optional, Dict, Any

class EPCClient:
    def __init__(self):
        self.api_key = os.getenv("EPC_API_KEY")
        self.base_url = "https://epc.opendatacommunities.org/api/v1/domestic/search"

    async def get_property_metrics(self, address: str) -> Dict[str, Any]:
        """Fetches floor area and current efficiency from real EPC records."""
        headers = {
            "Authorization": f"Basic {self.api_key}",
            "Accept": "application/json"
        }
        params = {"address": address, "size": 1}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.base_url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json().get("rows", [])
                    if data:
                        prop = data[0]
                        return {
                            "floor_area": float(prop.get("total-floor-area", 90)),
                            "current_energy_rating": prop.get("current-energy-rating", "D"),
                            "property_type": prop.get("property-type", "House"),
                            "built_form": prop.get("built-form", "Semi-Detached")
                        }
        except Exception as e:
            print(f"EPC API Error: {e}")
        
        # Fallback to national averages if API fails
        return {"floor_area": 90.0, "current_energy_rating": "D", "property_type": "House"}

epc_client = EPCClient()