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

# Updated imports to include our new functions
from helpers.value_calculator import calculate_value_increase, fetch_property_context

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


@app.get("/")
async def root():
    return {
        "message": "Proptech ROI Analysis API",
        "endpoints": {
            "GET /health": "Health check",
            "POST /api/analyze": "Analyze property retrofit feasibility, ROI, timeline"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/analyze", response_model=PropertyAnalysisResponse)
async def analyze_property(request: PropertyAnalysisRequest):
    print(f"\n{'='*70}")
    print(f"Analyzing Reference/Postcode: {request.property_reference} | Budget: £{request.budget:,.2f}")
    print(f"Improvements: {', '.join(request.desired_improvements)}")
    print(f"{'='*70}\n")
    
    try:
        # Treat the property_reference as a Postcode for the free tier APIs we are using
        postcode = request.property_reference
        
        # 1. Handle Location Data
        if request.latitude and request.longitude:
            latitude, longitude = request.latitude, request.longitude
            print(f"✓ Using provided coordinates ({latitude}, {longitude})")
        else:
            coords = await geocode_postcode(postcode)
            if not coords:
                raise HTTPException(status_code=400, detail=f"Invalid postcode or unable to geocode: {postcode}")
            latitude, longitude = coords

        # 2. Fetch actual property data (EPC rating and Land Registry Price Paid)
        current_epc, property_value = await fetch_property_context(postcode=postcode)
        
        # 3. Check local planning applications via IBex
        applications = await fetch_planning_applications(ibex_client, latitude, longitude)
        
        improvements_analysis = []
        total_cost = 0
        total_value_increase = 0
        
        for improvement_type in request.desired_improvements:
            print(f"\nAnalyzing: {improvement_type.upper()}")
            
            matching = filter_by_improvement_type(applications, improvement_type)
            approved_count = len(matching)
            
            avg_time = calculate_average_approval_time(matching)
            examples = extract_examples(matching, limit=5)
            
            estimated_cost, cost_explanation = calculate_cost(improvement_type, matching)
            
            # 4. Use real Land Registry & EPC Data for Valuation
            value_increase, value_explanation = calculate_value_increase(
                improvement_type=improvement_type, 
                estimated_cost=estimated_cost,
                current_epc=current_epc,
                property_value=property_value
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
                value_explanation=value_explanation,  # Passing the new explanation to the frontend!
                examples=examples
            ))
            
            total_cost += estimated_cost
            total_value_increase += value_increase
        
        total_roi = calculate_roi(total_cost, total_value_increase)
        within_budget, budget_text = check_budget(total_cost, request.budget)
        high_feasibility_count = sum(1 for imp in improvements_analysis if imp.feasibility == "HIGH")
        
        summary = generate_summary(
            postcode=postcode,
            num_improvements=len(request.desired_improvements),
            total_cost=total_cost,
            total_value_increase=total_value_increase,
            total_roi=total_roi,
            budget=request.budget,
            high_feasibility_count=high_feasibility_count,
            within_budget=within_budget
        )
        
        print(f"\n{'='*70}")
        print(f"TOTAL: £{total_cost:,} cost | £{total_value_increase:,.2f} value | {total_roi:.1f}% ROI")
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