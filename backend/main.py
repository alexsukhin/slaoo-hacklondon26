from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
from dotenv import load_dotenv

from models import PropertyAnalysisRequest, PropertyAnalysisResponse, ImprovementAnalysis
from ibex_client import IBexClient

from helpers.geocoding import geocode_postcode
from helpers.ibex_service import fetch_planning_applications
from helpers.application_filter import filter_by_improvement_type
from helpers.timeline_calculator import calculate_average_approval_time, extract_examples
from helpers.cost_calculator import calculate_cost, check_budget
from helpers.value_calculator import calculate_value_increase
from helpers.roi_calculator import calculate_roi
from helpers.feasibility_calculator import calculate_feasibility
from helpers.summary_generator import generate_summary

load_dotenv()

app = FastAPI(
    title="Proptech ROI Analysis API",
    description="Cost-benefit analysis for property energy efficiency upgrades",
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


@app.post("/api/property/analyze-by-address", response_model=PropertyAnalysisResponse)
async def analyze_by_address(address_query: str):
    try:
        # 1. Use IBex to resolve the address. 
        # (Internal fallback to postcode is already handled in ibex_client.py)
        target_property = await ibex_client.search_by_address(address_query)
        
        if not target_property or "geometry" not in target_property:
            raise HTTPException(status_code=404, detail="Address not found in IBex records.")

        # 2. Robust Coordinate Extraction [Fix 1]
        geom = target_property["geometry"]
        geom_type = geom.get("type")
        
        if geom_type == "Point":
            lng, lat = geom["coordinates"]
        elif geom_type == "Polygon":
            # Safely extract the first point of the exterior ring
            try:
                lng, lat = geom["coordinates"][0][0]
            except (IndexError, TypeError):
                # Fallback: check if the object has a pre-calculated centre_point extension
                if target_property.get("centre_point"):
                    lng = target_property["centre_point"].get("lon")
                    lat = target_property["centre_point"].get("lat")
                else:
                    raise HTTPException(status_code=400, detail="Invalid Polygon structure.")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported spatial format: {geom_type}")

        # 3. Perform analysis using the resolved coordinates
        applications = await ibex_client.search_by_location(
            latitude=lat,
            longitude=lng,
            radius=50, 
            date_from=(date.today() - timedelta(days=3650)).isoformat()
        )
        
        recommendations = []
        if isinstance(applications, list) and len(applications) > 0:
            recommendations.append(f"Found {len(applications)} historical records for this property.")
            
        return PropertyAnalysisResponse(
            property_reference=target_property.get("uprn") or target_property.get("planning_reference"),
            planning_applications=applications if isinstance(applications, list) else [],
            recommendations=recommendations
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
async def analyze_property(request: PropertyAnalysisRequest):
    print(f"\n{'='*70}")
    print(f"Analyzing: {request.property_reference} | Budget: £{request.budget:,.2f}")
    print(f"Improvements: {', '.join(request.desired_improvements)}")
    print(f"{'='*70}\n")
    
    try:
        # TODO: Get current EPC rating for property
        coords = await geocode_postcode(request.property_reference)
        if not coords:
            raise HTTPException(status_code=400, detail=f"Invalid postcode: {request.property_reference}")
        latitude, longitude = coords
        
        # TODO: Check Article 4 / conservation area restrictions
        applications = await fetch_planning_applications(ibex_client, latitude, longitude)
        
        improvements_analysis = []
        total_cost = 0
        total_value_increase = 0
        
        for improvement_type in request.desired_improvements:
            print(f"\nAnalyzing: {improvement_type.upper()}")
            
            # TODO: Improve search beyond string matching
            matching = filter_by_improvement_type(applications, improvement_type)
            approved_count = len(matching)
            
            avg_time = calculate_average_approval_time(matching)
            examples = extract_examples(matching, limit=5)
            
            # TODO: Use real cost data from similar properties
            estimated_cost, cost_explanation = calculate_cost(improvement_type, matching)
            
            # TODO: Join EPC + Price Paid datasets for accurate green premium
            value_increase, value_explanation = calculate_value_increase(
                improvement_type, 
                estimated_cost,
                property_value=None  # TODO: Get from Land Registry
            )
            
            roi = calculate_roi(estimated_cost, value_increase)
            feasibility = calculate_feasibility(approved_count)
            
            print(f"✓ {approved_count} examples | £{estimated_cost:,} cost | {roi:.1f}% ROI | {feasibility} feasibility")
            
            improvements_analysis.append(ImprovementAnalysis(
                improvement_type=improvement_type,
                feasibility=feasibility,
                approved_examples=approved_count,
                average_time_days=avg_time,
                estimated_cost=estimated_cost,
                estimated_roi_percent=roi,
                green_premium_value=value_increase,
                examples=examples
            ))
            
            total_cost += estimated_cost
            total_value_increase += value_increase
        
        total_roi = calculate_roi(total_cost, total_value_increase)
        within_budget, budget_text = check_budget(total_cost, request.budget)
        high_feasibility_count = sum(1 for imp in improvements_analysis if imp.feasibility == "HIGH")
        
        # TODO: Use LLM (Gemini) to generate intelligent summary
        summary = generate_summary(
            postcode=request.property_reference,
            num_improvements=len(request.desired_improvements),
            total_cost=total_cost,
            total_value_increase=total_value_increase,
            total_roi=total_roi,
            budget=request.budget,
            high_feasibility_count=high_feasibility_count,
            within_budget=within_budget
        )
        
        print(f"\n{'='*70}")
        print(f"TOTAL: £{total_cost:,} cost | £{total_value_increase:,} value | {total_roi:.1f}% ROI")
        print(f"{budget_text}")
        print(f"{'='*70}\n")
        
        return PropertyAnalysisResponse(
            property_reference=request.property_reference,
            location={"latitude": latitude, "longitude": longitude},
            budget=request.budget,
            improvements=improvements_analysis,
            total_cost=total_cost,
            total_roi_percent=total_roi,
            total_value_increase=total_value_increase,
            summary=summary
        )
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("   PROPTECH ROI ANALYSIS API")
    print("="*70)
    print("\n🏠 POST /api/analyze")
    print("👀 Docs: http://localhost:8000/docs\n")
    print("="*70 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
