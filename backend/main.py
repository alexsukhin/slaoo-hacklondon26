from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import httpx
from models import PropertyAnalysisResponse, ImprovementAnalysis, AddressAnalysisRequest
from ibex_client import IBexClient
from helpers.ibex_service import fetch_planning_applications
from helpers.application_filter import filter_by_improvement_type
from helpers.timeline_calculator import calculate_average_approval_time, extract_examples
from helpers.cost_calculator import calculate_cost, check_budget
from helpers.value_calculator import calculate_value_increase, fetch_property_context
from helpers.roi_calculator import calculate_roi
from helpers.feasibility_calculator import calculate_feasibility
from helpers.summary_generator import generate_summary
from helpers.epcClient import epc_client

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
async def analyze_by_address(request: AddressAnalysisRequest):
    try:
        # --- Step 1: Geocode address ---
        headers = {"User-Agent": "ProptechAnalysisApp/1.0"}
        params = {"q": request.address_query, "format": "json", "limit": 1, "countrycodes": "gb"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            geo_res = await client.get("https://nominatim.openstreetmap.org/search", params=params, headers=headers)
            geo_data = geo_res.json()

        if not geo_data:
            raise HTTPException(status_code=404, detail="Address not found.")

        latitude = float(geo_data[0]["lat"])
        longitude = float(geo_data[0]["lon"])
        display_name = geo_data[0]["display_name"]

        # --- Step 2: Fetch property context (EPC, Land Registry) ---
        current_epc, property_value, recommendations = await fetch_property_context(postcode=request.address_query)

        # --- Step 3: Fetch local planning applications via IBex ---
        applications = await fetch_planning_applications(ibex_client, latitude, longitude)

        # --- Step 4: Analyze each desired improvement ---
        improvements_analysis = []
        total_cost = 0
        total_value_increase = 0

        for improvement_type in request.desired_improvements:
            matching = filter_by_improvement_type(applications, improvement_type)
            avg_time = calculate_average_approval_time(matching)
            examples = extract_examples(matching, limit=5)

            # REVERTED to match your current cost_calculator.py signature
            estimated_cost, cost_explanation = calculate_cost(
                improvement_type=improvement_type, 
                matching_applications=matching
            )

            # FIXED: Removed duplicate argument and added missing comma
            value_increase, value_explanation = calculate_value_increase(
                improvement_type=improvement_type,
                estimated_cost=estimated_cost,
                current_epc=current_epc,
                property_value=property_value,
                recommendations=recommendations 
            )

            roi = calculate_roi(estimated_cost, value_increase)
            feasibility = calculate_feasibility(len(matching))

            improvements_analysis.append(ImprovementAnalysis(
                improvement_type=improvement_type,
                feasibility=feasibility,
                approved_examples=len(matching),
                average_time_days=avg_time,
                estimated_cost=estimated_cost,
                estimated_roi_percent=roi,
                green_premium_value=value_increase,
                value_explanation=value_explanation, 
                examples=examples
            ))

            total_cost += estimated_cost
            total_value_increase += value_increase

        # --- Step 5: Final ROI & Budget Calculation ---
        total_roi = calculate_roi(total_cost, total_value_increase)
        within_budget, _ = check_budget(total_cost, request.budget)

        summary = generate_summary(
            postcode=request.address_query,
            num_improvements=len(request.desired_improvements),
            total_cost=total_cost,
            total_value_increase=total_value_increase,
            total_roi=total_roi,
            budget=request.budget,
            high_feasibility_count=sum(1 for imp in improvements_analysis if imp.feasibility == "HIGH"),
            within_budget=within_budget
        )

        return PropertyAnalysisResponse(
            property_reference=display_name,
            location={"latitude": latitude, "longitude": longitude},
            budget=request.budget,
            improvements=improvements_analysis,
            total_cost=total_cost,
            total_roi_percent=total_roi,
            total_value_increase=total_value_increase,
            summary=summary
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("   PROPTECH ROI ANALYSIS API")
    print("="*70)
    print("\n🏠 POST /api/property/analyze-by-address")
    print("👀 Docs: http://localhost:8000/docs\n")
    print("="*70 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")