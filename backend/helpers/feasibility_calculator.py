import httpx

async def check_conservation_area(latitude: float, longitude: float) -> bool:
    """
    Check if the given coordinates fall within a UK Conservation Area
    using the planning.data.gov.uk open data API.
    """
    if latitude is None or longitude is None:
        return False
        
    url = "https://www.planning.data.gov.uk/entity.json"
    params = {
        "dataset": "conservation-area",
        "longitude": str(longitude),
        "latitude": str(latitude),
        "limit": 1
    }
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                entities = data.get("entities", [])
                if entities:
                    return True
    except Exception as e:
        print(f"[Conservation API] Error checking conservation area: {e}")
        
    return False

async def calculate_feasibility(
    improvement_type: str, 
    approved_count: int,
    latitude: float = None,
    longitude: float = None
) -> str:
    """
    Calculate feasibility rating based on number of approved examples,
    and cross-reference with Conservation Area restrictions.
    """
    in_conservation_area = False
    if latitude is not None and longitude is not None:
        in_conservation_area = await check_conservation_area(latitude, longitude)
    
    # Overrides for Conservation Areas
    if in_conservation_area:
        if improvement_type.lower() == "solar":
            return "LOW - Conservation Area"
        elif improvement_type.lower() == "windows":
            return "LOW - Conservation Area (Suggest Secondary Glazing)"
            
    # Standard logic
    if approved_count >= 3:
        return "HIGH"
    elif approved_count >= 1:
        return "MEDIUM"
    else:
        return "LOW"