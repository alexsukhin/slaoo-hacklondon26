import httpx
import os
import base64
import re 
from typing import Optional, Dict, Any

EPC_BAND_TO_NUMERIC = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}
NUMERIC_TO_EPC_BAND = {v: k for k, v in EPC_BAND_TO_NUMERIC.items()}

class EPCClient:
    def __init__(self):
        self.api_key = os.getenv("EPC_API_KEY")
        self.base_url = "https://epc.opendatacommunities.org/api/v1/domestic/search"

    # Updated signature to accept postcode
    async def get_property_metrics(self, address: str, postcode: str) -> Dict[str, Any]:
        """Fetches floor area and current efficiency from real EPC records."""
        headers = {
            "Authorization": f"Basic {self.api_key}",
            "Accept": "application/json"
        }
        
        # Extract the house number (e.g. "31" or "29A")
        match = re.search(r'\b(\d+[A-Za-z]?)\b', address)
        house_num = match.group(1).upper() if match else None

        # Query the API by postcode to get all properties on the street
        params = {"postcode": postcode, "size": 100}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.base_url, headers=headers, params=params)
                if response.status_code == 200:
                    rows = response.json().get("rows", [])
                    best_match = None
                    
                    if house_num and rows:
                        for row in rows:
                            addr1 = row.get("address1", "").upper()
                            addr_full = row.get("address", "").upper()
                            # Check if the exact house number is in the EPC address string
                            if addr1.startswith(house_num) or f" {house_num} " in f" {addr_full} ":
                                best_match = row
                                break
                    
                    if best_match:
                        return {
                            "floor_area": float(best_match.get("total-floor-area", 90)),
                            "current_energy_rating": best_match.get("current-energy-rating", "D"),
                            "property_type": best_match.get("property-type", "House"),
                            "built_form": best_match.get("built-form", "Semi-Detached")
                        }
        except Exception as e:
            print(f"EPC API Error: {e}")
        
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