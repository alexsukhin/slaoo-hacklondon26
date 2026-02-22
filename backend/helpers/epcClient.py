import httpx
import os
import re
import base64
from typing import Dict, Any

EPC_BAND_TO_NUMERIC = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}
NUMERIC_TO_EPC_BAND = {v: k for k, v in EPC_BAND_TO_NUMERIC.items()}

class EPCClient:
    def __init__(self):
        self.email = os.getenv("EPC_EMAIL")
        self.api_key = os.getenv("EPC_API_KEY")
        self.base_url = "https://epc.opendatacommunities.org/api/v1/domestic/search"

        self.improvement_scores = {
            "insulation": -1,
            "heat_pump": -2,
            "solar": -1,
            "windows": -1
        }

        # Use proper Basic Auth encoding: email:api_key
        if self.email and self.api_key:
            token_bytes = f"{self.email}:{self.api_key}".encode("utf-8")
            token_b64 = base64.b64encode(token_bytes).decode("utf-8")
            self.headers = {
                "Authorization": f"Basic {token_b64}",
                "Accept": "application/json"
            }
        else:
            raise ValueError("EPC_EMAIL and EPC_API_KEY must be set in environment variables")

    async def get_property_metrics(self, address: str, postcode: str) -> Dict[str, Any]:
        """Fetches floor area, EPC band, property type, and built form."""
        house_num = None
        match = re.search(r'\b(\d+[A-Za-z]?)\b', address)
        if match:
            house_num = match.group(1).upper()

        params = {"postcode": postcode, "size": 100}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.base_url, headers=self.headers, params=params)
                if response.status_code != 200:
                    print("broken")
                    return {
                        "floor_area": 90.0,
                        "current_energy_rating": "D",
                        "property_type": "House",
                        "built_form": "Semi-Detached"
                    }

                rows = response.json().get("rows", [])
                if not rows:
                    return {
                        "floor_area": 90.0,
                        "current_energy_rating": "D",
                        "property_type": "House",
                        "built_form": "Semi-Detached"
                    }

                # --- Step 1: exact house number match ---
                best_match = None
                if house_num:
                    for row in rows:
                        addr1 = row.get("address1", "").upper()
                        addr_full = row.get("address", "").upper()
                        if addr1.startswith(house_num) or f" {house_num} " in f" {addr_full} ":
                            best_match = row
                            break

                # --- Step 2: fallback to first row with valid energy rating ---
                if not best_match:
                    for row in rows:
                        rating = row.get("current-energy-rating")
                        if rating:
                            best_match = row
                            break

                # --- Step 3: final fallback ---
                if not best_match:
                    best_match = rows[0]

                return {
                    "floor_area": float(best_match.get("total-floor-area", 90)),
                    "current_energy_rating": best_match.get("current-energy-rating", "D").upper(),
                    "property_type": best_match.get("property-type", "House"),
                    "built_form": best_match.get("built-form", "Semi-Detached")
                }

        except Exception as e:
            print(f"[EPC API] Error: {e}")
            return {
                "floor_area": 90.0,
                "current_energy_rating": "D",
                "property_type": "House",
                "built_form": "Semi-Detached"
            }

    def estimate_epc_after_improvements(self, current_band: str, improvements: list[str]) -> str:
        """Estimate EPC band cumulatively for multiple improvements."""
        numeric = EPC_BAND_TO_NUMERIC.get(current_band.upper(), 4)
        for imp in improvements:
            numeric += self.improvement_scores.get(imp, 0)
        numeric = max(1, min(7, round(numeric)))
        return NUMERIC_TO_EPC_BAND[numeric]