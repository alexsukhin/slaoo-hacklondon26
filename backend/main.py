from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import re
from dotenv import load_dotenv
import httpx
from models import PropertyAnalysisResponse, ImprovementAnalysis, AddressAnalysisRequest, EnergyCompliance
from ibex_client import IBexClient
from helpers.ibex_service import fetch_planning_applications
from helpers.application_filter import filter_by_improvement_type
from helpers.timeline_calculator import calculate_average_approval_time, extract_examples
from helpers.cost_calculator import calculate_cost, check_budget
from helpers.value_calculator import calculate_value_increase, fetch_property_context
from helpers.roi_calculator import calculate_roi
from helpers.feasibility_calculator import calculate_feasibility
from helpers.summary_generator import generate_summary
from helpers.epcClient import EPCClient

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
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")

ibex_client = IBexClient(IBEX_API_KEY, IBEX_BASE_URL)
epc_client = EPCClient()

EPC_BAND_TO_NUMERIC = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7}
NUMERIC_TO_EPC_BAND = {v: k for k, v in EPC_BAND_TO_NUMERIC.items()}

@app.get("/api/config")
def get_config():
    return {"mapboxToken": MAPBOX_TOKEN}

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
        
        # --- Step 1.5: Extract Postcode ---
        # We moved this UP so the EPC client can use it!
        postcode_match = re.search(r'[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}', request.address_query.upper())
        extracted_postcode = postcode_match.group(0) if postcode_match else request.address_query

        # --- Step 2: Fetch property context (EPC Metrics) ---
        # Pass both the raw address AND the clean postcode
        property_metrics = await epc_client.get_property_metrics(request.address_query, extracted_postcode)

        current_epc = property_metrics.get("current_energy_rating", "D")

        epc_per_improvement = {}
        
        for imp in request.desired_improvements:
            projected = epc_client.estimate_epc_after_improvements(
                current_band=current_epc,
                improvements=[imp]
            )
            epc_per_improvement[imp] = projected

        best_improvement = None
        best_band_value = 999

        for imp, band in epc_per_improvement.items():
            band_value = EPC_BAND_TO_NUMERIC[band]

            if band_value < best_band_value:
                best_band_value = band_value
                best_improvement = imp

        projected_epc = epc_per_improvement[best_improvement]

        # Compliance status
        compliance_status = "ON TRACK" if EPC_BAND_TO_NUMERIC[projected_epc] <= EPC_BAND_TO_NUMERIC["C"] else "OFF TRACK"

        # Optional: suggest remaining improvements not selected
        suggestions = []
        if compliance_status != "ON TRACK":
            for imp in ["insulation", "heat_pump", "solar", "windows"]:
                if imp not in request.desired_improvements:
                    suggestions.append(imp.capitalize())
        
        # --- Step 2.5: Fetch Value Context ---
        current_epc, property_value, recommendations = await fetch_property_context(
            address=request.address_query, 
            postcode=extracted_postcode
        )

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

            estimated_cost, cost_explanation = calculate_cost(
                improvement_type=improvement_type, 
                matching_applications=matching,
                property_metrics=property_metrics
            )

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
            postcode=extracted_postcode,
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
            summary=summary,
            energy_compliance=EnergyCompliance(
                current_epc=current_epc,
                projected_epc=projected_epc,
                compliance_status=compliance_status,
                suggested_improvements=suggestions
            )
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