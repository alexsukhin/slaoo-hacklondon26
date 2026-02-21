import httpx
import os
import base64
from typing import Optional, Tuple, List, Dict, Any

EPC_PREMIUMS = {'A': 0.14, 'B': 0.10, 'C': 0.05, 'D': 0.00, 'E': -0.05, 'F': -0.08, 'G': -0.12}
EXPECTED_EPC_JUMP = {"solar": 1, "insulation": 2, "windows": 1, "heat_pump": 2}
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

async def fetch_land_registry_price(postcode: str) -> Optional[float]:
    """Queries the live HM Land Registry SPARQL API for recent sales in a postcode."""
    clean_postcode = postcode.strip().upper()
    if " " not in clean_postcode and len(clean_postcode) > 3:
        clean_postcode = f"{clean_postcode[:-3]} {clean_postcode[-3:]}"
        
    query = f"""
    PREFIX lrppi: <http://landregistry.data.gov.uk/def/ppi/>
    PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>
    SELECT ?amount
    WHERE {{
      ?transx lrppi:pricePaid ?amount ;
              lrppi:transactionDate ?date ;
              lrppi:propertyAddress ?addr .
      ?addr lrcommon:postcode "{clean_postcode}" .
    }}
    ORDER BY DESC(?date)
    LIMIT 1
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
                    price = float(results[0]["amount"]["value"])
                    print(f"[Land Registry API] Found recent sale: £{price:,.2f} for {clean_postcode}")
                    return price
            print(f"[Land Registry API] No sales found for {clean_postcode}")
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

async def fetch_property_context(postcode: str) -> Tuple[str, float, List[Dict[str, Any]]]:
    """Fetches real EPC rating, property value, and property-specific recommendations."""
    current_epc = 'D' # Default baseline
    recommendations = []
    
    property_value = await fetch_land_registry_price(postcode)
    if not property_value:
        property_value = await fetch_district_average_price(postcode)
    
    epc_api_key = os.getenv("EPC_API_KEY")
    if epc_api_key:
        encoded_key = base64.b64encode(epc_api_key.encode('utf-8')).decode('utf-8')
        headers = {
            "Authorization": f"Basic {encoded_key}",
            "Accept": "application/json"
        }
        try:
            clean_postcode = postcode.replace(" ", "").upper()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://epc.opendatacommunities.org/api/v1/domestic/search?postcode={clean_postcode}",
                    headers=headers
                )
                if response.status_code == 200:
                    rows = response.json().get('rows', [])
                    if rows:
                        current_epc = rows[0].get('current-energy-rating', 'D').upper()
                        print(f"[EPC API] Found rating {current_epc} for {postcode}")
                        
                        # NEW: Fetch the actual recommendations for this property
                        lmk_key = rows[0].get('lmk-key')
                        if lmk_key:
                            recommendations = await fetch_epc_recommendations(lmk_key, headers)
                            print(f"[EPC API] Found {len(recommendations)} official recommendations")
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
            "solar": ["solar", "photovoltaic", "pv"],
            "insulation": ["insulation", "cavity", "solid wall", "loft", "roof"],
            "windows": ["glazing", "double glazed", "secondary glazing", "window"],
            "heat_pump": ["heat pump", "air source", "ground source"]
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