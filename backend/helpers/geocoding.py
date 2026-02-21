import httpx
from typing import Optional, Tuple


async def geocode_postcode(postcode: str) -> Optional[Tuple[float, float]]:
    """Geocode UK postcode to coordinates using free postcodes.io API"""
    try:
        postcode_clean = postcode.strip().replace(" ", "")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.postcodes.io/postcodes/{postcode_clean}")
            if response.status_code == 200:
                data = response.json()
                if data.get("result"):
                    lat = data["result"]["latitude"]
                    lon = data["result"]["longitude"]
                    print(f"✓ Geocoded postcode {postcode} to ({lat}, {lon})")
                    return (lat, lon)
    except Exception as e:
        print(f"✗ Geocoding failed for {postcode}: {str(e)}")
    
    return None
