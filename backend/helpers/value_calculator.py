import httpx
import os
import base64
from typing import Optional, Tuple

EPC_PREMIUMS = {'A': 0.14, 'B': 0.10, 'C': 0.05, 'D': 0.00, 'E': -0.05, 'F': -0.08, 'G': -0.12}
EXPECTED_EPC_JUMP = {"solar": 1, "insulation": 2, "windows": 1, "heat_pump": 2}
EPC_BANDS = ['G', 'F', 'E', 'D', 'C', 'B', 'A']

async def fetch_land_registry_price(postcode: str) -> Optional[float]:
    """Queries the live HM Land Registry SPARQL API for recent sales in a postcode."""
    # Format postcode perfectly for the API (e.g., "SW1A 1AA")
    clean_postcode = postcode.strip().upper()
    if " " not in clean_postcode and len(clean_postcode) > 3:
        clean_postcode = f"{clean_postcode[:-3]} {clean_postcode[-3:]}"
        
    # A SPARQL query to get the most recent transaction price for this postcode
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

async def fetch_property_context(postcode: str) -> Tuple[str, Optional[float]]:
    """Fetches real EPC rating from DLUHC API and last-sold price from Land Registry API."""
    current_epc = 'D' # Default baseline
    property_value = None
    
    # 1. Fetch Real Land Registry Data (Live API)
    property_value = await fetch_land_registry_price(postcode)
    
    # 2. Fetch Real EPC Data
    epc_api_key = os.getenv("EPC_API_KEY")
    if epc_api_key:
        # Base64 encode the email:apikey string
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
        except Exception as e:
            print(f"[EPC API] Error: {e}")

    return current_epc, property_value

def calculate_value_increase(improvement_type: str, estimated_cost: float, current_epc: str, property_value: Optional[float] = None) -> Tuple[float, str]:
    """Calculates ROI based on EPC band jump and real property value."""
    improvement_key = improvement_type.lower()
    
    current_index = EPC_BANDS.index(current_epc)
    band_jump = EXPECTED_EPC_JUMP.get(improvement_key, 1)
    new_index = min(current_index + band_jump, len(EPC_BANDS) - 1)
    new_epc = EPC_BANDS[new_index]
    
    current_premium = EPC_PREMIUMS[current_epc]
    new_premium = EPC_PREMIUMS[new_epc]
    net_premium_increase = new_premium - current_premium
    
    if property_value:
        value_increase = property_value * net_premium_increase
        explanation = f"Boosts EPC from {current_epc} to {new_epc}. Based on a {net_premium_increase*100:.1f}% market premium on real local property value (£{property_value:,.0f})."
    else:
        value_increase = estimated_cost * (net_premium_increase * 100)
        explanation = f"Boosts EPC from {current_epc} to {new_epc}. Estimated {(net_premium_increase*100):.1f}% green premium (Land Registry data missing)."
    
    if value_increase <= 0:
        value_increase = estimated_cost * 0.5
        explanation = f"Property is already highly efficient ({current_epc}). Value increase reflects partial cost retention."
        
    return value_increase, explanation