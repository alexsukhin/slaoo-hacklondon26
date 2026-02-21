import httpx
from typing import Optional, Tuple


async def geocode_uprn(uprn: str) -> Optional[Tuple[float, float]]:
    """
    Geocode UPRN to lat/long coordinates
    For MVP: Returns mock coordinates
    TODO: Integrate with OS Places API or similar geocoding service
    """
    
    # Mock geocoding for common test UPRNs
    mock_data = {
        "UPRN100023336956": (51.5074, -0.1278),  # London
        "UPRN10008352341": (51.5465, -0.1436),   # Camden
        "UPRN10091234567": (53.4808, -2.2426),   # Manchester
    }
    
    if uprn in mock_data:
        return mock_data[uprn]
    
    # For hackathon: Use default London coordinates
    # In production, call OS Places API or similar:
    # https://api.os.uk/search/places/v1/uprn?uprn={uprn}&key={api_key}
    
    print(f"⚠️  UPRN {uprn} not in mock data, using default London coordinates")
    return (51.5074, -0.1278)


async def geocode_postcode(postcode: str) -> Optional[Tuple[float, float]]:
    """
    Geocode UK postcode to coordinates using free postcodes.io API
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.postcodes.io/postcodes/{postcode}")
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
