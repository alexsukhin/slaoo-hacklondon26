import httpx
import os
import re
import base64
from typing import Optional, Tuple, List, Dict, Any

EPC_PREMIUMS = {'A': 0.14, 'B': 0.10, 'C': 0.05, 'D': 0.00, 'E': -0.05, 'F': -0.08, 'G': -0.12}
EXPECTED_EPC_JUMP = {"solar": 1, "insulation": 2, "windows": 1, "heat_pump": 2,
                     "battery": 1, "loft_conversion": 1, "cladding": 1, "ev_charger": 1}
EPC_BANDS = ['G', 'F', 'E', 'D', 'C', 'B', 'A']

async def fetch_district_average_price(postcode: str) -> Optional[float]:
    """Queries HM Land Registry for the average price in the postcode district (e.g., N11)."""
    clean_postcode = postcode.strip().upper()
    if " " not in clean_postcode and len(clean_postcode) > 3:
        clean_postcode = f"{clean_postcode[:-3]} {clean_postcode[-3:]}"
        
    outward_code = clean_postcode.split(" ")[0]
    
    query = f"""
    PREFIX lrppi: <http://landregistry.data.gov.uk/def/ppi/>
    PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>
    SELECT (AVG(?amount) as ?avgPrice)
    WHERE {{
      ?transx lrppi:pricePaid ?amount ;
              lrppi:propertyAddress ?addr .
      ?addr lrcommon:postcode ?pc .
      FILTER(STRSTARTS(STR(?pc), "{outward_code} "))
    }}
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "http://landregistry.data.gov.uk/landregistry/query",
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"}
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", {}).get("bindings", [])
                if results and "avgPrice" in results[0] and "value" in results[0]["avgPrice"]:
                    avg_price = float(results[0]["avgPrice"]["value"])
                    print(f"[Land Registry API] Found district average: £{avg_price:,.2f} for {outward_code}")
                    return avg_price
    except Exception as e:
        print(f"[Land Registry API] Error fetching district average: {e}")
        
    return 285000.0 # Ultimate fallback: UK National Average

async def fetch_land_registry_price(address: str, postcode: str) -> Optional[float]:
    """Queries HM Land Registry for recent sales, attempting to find the specific house."""
    clean_postcode = postcode.strip().upper()
    if " " not in clean_postcode and len(clean_postcode) > 3:
        clean_postcode = f"{clean_postcode[:-3]} {clean_postcode[-3:]}"
        
    match = re.search(r'\b(\d+[A-Za-z]?)\b', address)
    house_num = match.group(1).upper() if match else None

    # Fetch top 100 recent sales in the postcode
    query = f"""
    PREFIX lrppi: <http://landregistry.data.gov.uk/def/ppi/>
    PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>
    SELECT ?amount ?paon ?saon ?date
    WHERE {{
      ?transx lrppi:pricePaid ?amount ;
              lrppi:transactionDate ?date ;
              lrppi:propertyAddress ?addr .
      ?addr lrcommon:postcode "{clean_postcode}" .
      OPTIONAL {{ ?addr lrcommon:paon ?paon . }}
      OPTIONAL {{ ?addr lrcommon:saon ?saon . }}
    }}
    ORDER BY DESC(?date)
    LIMIT 100
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://landregistry.data.gov.uk/landregistry/query",
                data={"query": query},
                headers={"Accept": "application/sparql-results+json"}
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", {}).get("bindings", [])
                
                if results:
                    # 1. Try to find the exact house number (PAON or SAON)
                    if house_num:
                        for r in results:
                            paon = r.get("paon", {}).get("value", "").upper()
                            saon = r.get("saon", {}).get("value", "").upper()
                            if house_num == paon or house_num == saon:
                                price = float(r["amount"]["value"])
                                print(f"[Land Registry API] Found exact sale for '{house_num}' at {clean_postcode}: £{price:,.2f}")
                                return price
                    
                    # 2. If exact match not found, compute average of recent sales in the postcode 
                    # (Much more accurate than picking a random neighbor's sale)
                    prices = [float(r["amount"]["value"]) for r in results]
                    avg_price = sum(prices) / len(prices)
                    print(f"[Land Registry API] Exact property not found. Using recent average for {clean_postcode}: £{avg_price:,.2f}")
                    return avg_price
                    
    except Exception as e:
        print(f"[Land Registry API] Error fetching data: {e}")
    return None

async def fetch_epc_recommendations(lmk_key: str, headers: dict) -> List[Dict[str, Any]]:
    """Fetches the actual assessor recommendations for a specific EPC certificate."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://epc.opendatacommunities.org/api/v1/domestic/recommendations/{lmk_key}",
                headers=headers
            )
            if response.status_code == 200:
                return response.json().get('rows', [])
    except Exception as e:
        print(f"[EPC API] Error fetching recommendations: {e}")
    return []

# Update the function signature to accept both address and postcode
async def fetch_property_context(address: str, postcode: str) -> Tuple[str, float, List[Dict[str, Any]]]:
    current_epc = 'D' # Default baseline
    recommendations = []
    
    # Land registry now uses both address and postcode to find the exact property
    property_value = await fetch_land_registry_price(address, postcode)
    if not property_value:
        property_value = await fetch_district_average_price(postcode)
    
    epc_api_key = os.getenv("EPC_API_KEY")
    if epc_api_key:
        encoded_key = base64.b64encode(epc_api_key.encode('utf-8')).decode('utf-8')
        headers = {
            "Authorization": f"Basic {encoded_key}",
            "Accept": "application/json"
        }
        
        match = re.search(r'\b(\d+[A-Za-z]?)\b', address)
        house_num = match.group(1).upper() if match else None

        try:
            async with httpx.AsyncClient() as client:
                # Query EPC by Postcode instead of full address string
                response = await client.get(
                    "https://epc.opendatacommunities.org/api/v1/domestic/search",
                    params={"postcode": postcode, "size": 100},
                    headers=headers
                )
                if response.status_code == 200:
                    rows = response.json().get('rows', [])
                    best_match = None
                    
                    if house_num and rows:
                        for row in rows:
                            addr1 = row.get("address1", "").upper()
                            addr_full = row.get("address", "").upper()
                            # Check if the primary address line starts with the house number
                            if addr1.startswith(house_num) or f" {house_num} " in f" {addr_full} ":
                                best_match = row
                                break

                    if best_match:
                        current_epc = best_match.get('current-energy-rating', 'D').upper()
                        print(f"[EPC API] Found exact rating {current_epc} for {address}")
                        
                        lmk_key = best_match.get('lmk-key')
                        if lmk_key:
                            recommendations = await fetch_epc_recommendations(lmk_key, headers)
                            print(f"[EPC API] Found {len(recommendations)} official recommendations")
                    else:
                        print(f"[EPC API] Could not find exact house '{house_num}' in {postcode}. Defaulting to D.")
        except Exception as e:
            print(f"[EPC API] Error: {e}")

    return current_epc, property_value, recommendations

def calculate_value_increase(
    improvement_type: str, 
    estimated_cost: float, 
    current_epc: str, 
    property_value: Optional[float] = None,
    recommendations: Optional[List[Dict[str, Any]]] = None
) -> Tuple[float, str]:
    """Calculates ROI using real EPC recommendations where available, with a static fallback."""
    improvement_key = improvement_type.lower()
    current_index = EPC_BANDS.index(current_epc)
    
    new_epc = None
    used_real_recommendation = False
    
    # 1. Check if the improvement is officially recommended and get its exact band jump
    if recommendations:
        # Keywords map our front-end terms to the EPC API descriptions
        EPC_KEYWORD_MAP = {
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
        keywords = EPC_KEYWORD_MAP.get(improvement_key, [])
        
        for rec in recommendations:
            item = rec.get("improvement-item", "").lower()
            if any(kw in item for kw in keywords):
                rec_band = rec.get("potential-energy-rating", "").upper()
                if rec_band in EPC_BANDS:
                    rec_index = EPC_BANDS.index(rec_band)
                    # Only accept it if it actually improves the rating
                    if rec_index > current_index:
                        new_epc = rec_band
                        used_real_recommendation = True
                        break

    # 2. Fallback to hardcoded estimates if it wasn't recommended or no EPC data found
    if not new_epc:
        band_jump = EXPECTED_EPC_JUMP.get(improvement_key, 1)
        new_index = min(current_index + band_jump, len(EPC_BANDS) - 1)
        new_epc = EPC_BANDS[new_index]
    
    current_premium = EPC_PREMIUMS[current_epc]
    new_premium = EPC_PREMIUMS[new_epc]
    net_premium_increase = new_premium - current_premium
    
    if property_value:
        value_increase = property_value * net_premium_increase
        
        # Build a smarter explanation based on how we got the data
        if used_real_recommendation:
            explanation = f"Officially recommended on property's EPC. Expected to boost rating from {current_epc} to {new_epc}. Based on a {(net_premium_increase*100):.1f}% market premium on local property value (£{property_value:,.0f})."
        else:
            explanation = f"Estimated to boost EPC from {current_epc} to {new_epc}. Based on a {(net_premium_increase*100):.1f}% market premium on local property value (£{property_value:,.0f})."
    else:
        # Failsafe logic
        value_increase = 285000 * net_premium_increase
        explanation = f"Boosts EPC from {current_epc} to {new_epc}. Estimated {(net_premium_increase*100):.1f}% green premium (Using national average value)."
    
    if value_increase <= 0:
        value_increase = estimated_cost * 0.5
        explanation = f"Property is already highly efficient ({current_epc}). Value increase reflects partial cost retention rather than a market premium jump."
        
    return value_increase, explanation