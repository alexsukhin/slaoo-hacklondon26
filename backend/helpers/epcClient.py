import httpx
import os
import base64
from typing import Optional, Dict, Any

EPC_BAND_TO_NUMERIC = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}
NUMERIC_TO_EPC_BAND = {v: k for k, v in EPC_BAND_TO_NUMERIC.items()}

class EPCClient:
    def __init__(self):
        self.api_key = os.getenv("EPC_API_KEY")
        self.base_url = "https://epc.opendatacommunities.org/api/v1/domestic/search"

        # Define per-improvement impact as numeric deltas
        # Negative numbers improve EPC (lower numeric = better band)
        self.improvement_scores = {
            "insulation": -1.0,
            "heat_pump": -1.0,
            "solar": -0.5,
            "windows": -0.5
        }

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

        # Fallback to national averages
        return {"floor_area": 90.0, "current_energy_rating": "D", "property_type": "House"}

    def estimate_epc_after_improvements(
        self, current_band: str, improvements: list[str]
    ) -> str:
        """
        Estimate EPC band cumulatively for multiple improvements.
        Each improvement adds its effect rather than just taking the best.
        """
        numeric = EPC_BAND_TO_NUMERIC.get(current_band.upper(), 4)  # default D

        for imp in improvements:
            numeric += self.improvement_scores.get(imp, 0)  # add delta

        # Clamp and round
        numeric = max(1, min(7, numeric))
        numeric = round(numeric)

        return NUMERIC_TO_EPC_BAND[numeric]