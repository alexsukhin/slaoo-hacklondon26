from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
from datetime import date, datetime, timedelta
import os
import httpx
from dotenv import load_dotenv

from models import (
    PropertySearchRequest,
    AreaAnalysisRequest,
    RetrofitAnalysisRequest,
    PropertyAnalysisResponse,
    PlanningApplicationFilter
)
from ibex_client import IBexClient

load_dotenv()

app = FastAPI(
    title="Proptech Analysis API",
    description="API for property energy efficiency and planning analysis",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IBEX_API_KEY = os.getenv("IBEX_API_KEY", "")
IBEX_BASE_URL = os.getenv("IBEX_BASE_URL", "https://ibex.seractech.co.uk")

ibex_client = IBexClient(IBEX_API_KEY, IBEX_BASE_URL)


@app.get("/")
async def root():
    return {
        "message": "Proptech Analysis API",
        "endpoints": {
            "GET /health": "Health check",
            "POST /api/property/analyze": "Analyze property with planning data",
            "POST /api/area/retrofits": "Find retrofit projects in area",
            "GET /api/planning/search": "Search planning applications",
            "POST /api/planning/search": "Search planning applications (POST)",
            "GET /api/council/{council_id}/stats": "Get council statistics"
        }
    }


@app.get("/health")
async def health_check():
    print("[Health] Health check requested")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# In backend/main.py

@app.post("/api/property/analyze-by-address", response_model=PropertyAnalysisResponse)
async def analyze_by_address(address_query: str):
    try:
        # STEP 1: Geocode the address using OpenStreetMap (Nominatim)
        # Nominatim requires a User-Agent header as per their policy
        headers = {"User-Agent": "ProptechAnalysisApp/1.0"}
        params = {
            "q": address_query,
            "format": "json",
            "limit": 1,
            "countrycodes": "gb" # Restrict to UK
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            geo_response = await client.get(
                "https://nominatim.openstreetmap.org/search", 
                params=params, 
                headers=headers
            )
            geo_data = geo_response.json()

        if not geo_data:
            raise HTTPException(status_code=404, detail="Could not find coordinates for this address.")

        lat = float(geo_data[0]["lat"])
        lng = float(geo_data[0]["lon"])
        display_name = geo_data[0]["display_name"]

        # STEP 2: Use the resolved coordinates to search IBex
        # Search for applications within 50m of this geocoded point
        applications = await ibex_client.search_by_location(
            latitude=lat,
            longitude=lng,
            radius=50,
            date_from=(date.today() - timedelta(days=3650)).isoformat()
        )
        
        return PropertyAnalysisResponse(
            property_reference=None, # OSM doesn't provide UPRNs
            planning_applications=applications if isinstance(applications, list) else [],
            recommendations=[f"Located at: {display_name}"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/area/retrofits")
async def find_area_retrofits(request: RetrofitAnalysisRequest):
    print(f"\n[Retrofit Analysis] Searching for {request.improvement_type} retrofits")
    print(f"[Retrofit Analysis] Location: ({request.latitude}, {request.longitude}), radius: {request.radius}m")
    
    try:
        date_to = date.today().isoformat()
        date_from = (date.today() - timedelta(days=1095)).isoformat()
        
        improvement_keywords = {
            "solar": ["solar", "photovoltaic", "pv panel"],
            "insulation": ["insulation", "wall insulation", "external wall", "internal wall"],
            "windows": ["window", "double glazing", "triple glazing"],
            "heat_pump": ["heat pump", "air source", "ground source"],
        }
        
        keywords = improvement_keywords.get(request.improvement_type.lower(), [request.improvement_type])
        
        filters = {
            "normalised_decision": ["Approved"],
            "normalised_application_type": ["full planning application", "householder planning application"]
        }
        
        applications = await ibex_client.search_by_location(
            latitude=request.latitude,
            longitude=request.longitude,
            radius=request.radius,
            date_from=date_from,
            date_to=date_to,
            filters=filters
        )
        
        filtered_retrofits = []
        if isinstance(applications, list):
            for app in applications:
                proposal = app.get("proposal", "").lower()
                if any(keyword in proposal for keyword in keywords):
                    filtered_retrofits.append(app)
                    print(f"[Retrofit Analysis] Match found: {app.get('planning_reference')} - {app.get('proposal')[:100]}")
        
        print(f"[Retrofit Analysis] Found {len(filtered_retrofits)} matching retrofits out of {len(applications) if isinstance(applications, list) else 0} total applications")
        
        return {
            "improvement_type": request.improvement_type,
            "total_matches": len(filtered_retrofits),
            "retrofits": filtered_retrofits,
            "area_info": {
                "latitude": request.latitude,
                "longitude": request.longitude,
                "radius_meters": request.radius
            }
        }
    
    except Exception as e:
        print(f"[Retrofit Analysis] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Retrofit search failed: {str(e)}")


@app.get("/api/planning/search")
@app.post("/api/planning/search")
async def search_planning_applications(
    latitude: float = Query(..., description="Latitude"),
    longitude: float = Query(..., description="Longitude"),
    radius: int = Query(default=500, ge=50, le=2000, description="Search radius in meters"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    decision_filter: Optional[List[str]] = Query(None, description="Filter by decision status")
):
    print(f"\n[Planning Search] Searching at ({latitude}, {longitude}), radius: {radius}m")
    
    try:
        if not date_from:
            date_from = (date.today() - timedelta(days=365)).isoformat()
        if not date_to:
            date_to = date.today().isoformat()
        
        filters = {}
        if decision_filter:
            filters["normalised_decision"] = decision_filter
        
        applications = await ibex_client.search_by_location(
            latitude=latitude,
            longitude=longitude,
            radius=radius,
            date_from=date_from,
            date_to=date_to,
            filters=filters if filters else None
        )
        
        print(f"[Planning Search] Returning {len(applications) if isinstance(applications, list) else 0} applications")
        
        return {
            "total_results": len(applications) if isinstance(applications, list) else 0,
            "search_params": {
                "latitude": latitude,
                "longitude": longitude,
                "radius": radius,
                "date_from": date_from,
                "date_to": date_to
            },
            "applications": applications
        }
    
    except Exception as e:
        print(f"[Planning Search] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/api/council/{council_id}/stats")
async def get_council_statistics(
    council_id: int,
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    print(f"\n[Council Stats] Fetching statistics for council {council_id}")
    
    try:
        if not date_from:
            date_from = (date.today() - timedelta(days=365)).isoformat()
        if not date_to:
            date_to = date.today().isoformat()
        
        stats = await ibex_client.get_council_stats(
            council_id=council_id,
            date_from=date_from,
            date_to=date_to
        )
        
        print(f"[Council Stats] Retrieved stats: {stats}")
        
        return {
            "council_id": council_id,
            "date_range": {
                "from": date_from,
                "to": date_to
            },
            "statistics": stats
        }
    
    except Exception as e:
        print(f"[Council Stats] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get council stats: {str(e)}")


# takes long and lat as input 
@app.post("/api/area/analysis")
async def analyze_area(request: AreaAnalysisRequest):
    print(f"\n[Area Analysis] Analyzing area at ({request.latitude}, {request.longitude})")
    
    try:
        date_to = request.date_to.isoformat() if request.date_to else date.today().isoformat()
        date_from = request.date_from.isoformat() if request.date_from else (date.today() - timedelta(days=730)).isoformat()
        
        applications = await ibex_client.search_by_location(
            latitude=request.latitude,
            longitude=request.longitude,
            radius=request.radius,
            date_from=date_from,
            date_to=date_to
        )
        
        analysis = {
            "total_applications": len(applications) if isinstance(applications, list) else 0,
            "approved": 0,
            "refused": 0,
            "pending": 0,
            "project_types": {},
            "average_decision_time_days": 0
        }
        
        if isinstance(applications, list):
            decision_times = []
            
            for app in applications:
                decision = app.get("normalised_decision", "pending")
                if decision == "Approved":
                    analysis["approved"] += 1
                elif decision == "Refused":
                    analysis["refused"] += 1
                else:
                    analysis["pending"] += 1
                
                project_type = app.get("project_type", "unknown")
                analysis["project_types"][project_type] = analysis["project_types"].get(project_type, 0) + 1
                
                if app.get("application_date") and app.get("decided_date"):
                    try:
                        app_date = datetime.fromisoformat(app["application_date"].replace('Z', '+00:00'))
                        dec_date = datetime.fromisoformat(app["decided_date"].replace('Z', '+00:00'))
                        decision_times.append((dec_date - app_date).days)
                    except:
                        pass
            
            if decision_times:
                analysis["average_decision_time_days"] = sum(decision_times) / len(decision_times)
        
        print(f"[Area Analysis] Analysis complete: {analysis}")
        
        return {
            "location": {
                "latitude": request.latitude,
                "longitude": request.longitude,
                "radius_meters": request.radius
            },
            "date_range": {
                "from": date_from,
                "to": date_to
            },
            "analysis": analysis,
            "applications": applications if isinstance(applications, list) else []
        }
    
    except Exception as e:
        print(f"[Area Analysis] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Area analysis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("Starting Proptech Analysis API")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
