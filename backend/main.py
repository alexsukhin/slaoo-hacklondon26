from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from models import (
    PropertyAnalysisRequest,
    PropertyAnalysisResponse,
    ImprovementAnalysis,
    RetrofitExample
)
from ibex_client import IBexClient
from geocoding import geocode_uprn

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
        "message": "Proptech ROI Analysis API - MVP",
        "description": "Cost-benefit analysis for property energy efficiency upgrades",
        "endpoints": {
            "GET /health": "Health check",
            "POST /api/analyze": "Analyze property retrofit feasibility, ROI, and timeline"
        }
    }


@app.get("/health")
async def health_check():
    print("[Health] Health check requested")
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/analyze")
async def analyze_property(request: PropertyAnalysisRequest):
    print(f"\n{'='*70}")
    print(f"PROPERTY RETROFIT ANALYSIS")
    print(f"{'='*70}")
    print(f"Property: {request.property_reference}")
    print(f"Budget: £{request.budget:,.2f}")
    print(f"Desired Improvements: {', '.join(request.desired_improvements)}")
    
    # Geocode UPRN if coordinates not provided
    if not request.latitude or not request.longitude:
        print(f"📍 Geocoding UPRN: {request.property_reference}...")
        coords = await geocode_uprn(request.property_reference)
        if coords:
            request.latitude, request.longitude = coords
            print(f"✓ Geocoded to: ({request.latitude}, {request.longitude})")
        else:
            raise HTTPException(status_code=400, detail="Could not geocode property reference")
    
    print(f"Location: ({request.latitude}, {request.longitude})")
    print(f"{'='*70}\n")
    
    try:
        date_to = datetime.now().date().isoformat()
        date_from = (datetime.now().date() - timedelta(days=1095)).isoformat()
        
        IMPROVEMENT_KEYWORDS = {
            "solar": ["solar", "photovoltaic", "pv panel", "solar panel"],
            "insulation": ["insulation", "wall insulation", "external wall", "cavity wall"],
            "windows": ["window", "double glaz", "triple glaz", "glazing"],
            "heat_pump": ["heat pump", "air source", "ground source", "ashp", "gshp"]
        }
        
        ESTIMATED_COSTS = {
            "solar": 7000,
            "insulation": 4500,
            "windows": 5500,
            "heat_pump": 12000
        }
        
        GREEN_PREMIUM = {
            "solar": 3.5,
            "insulation": 2.8,
            "windows": 2.2,
            "heat_pump": 4.2
        }
        
        print(f"🔍 Searching for retrofit examples in 500m radius...\n")
        
        applications = await ibex_client.search_by_location(
            latitude=request.latitude,
            longitude=request.longitude,
            radius=500,
            date_from=date_from,
            date_to=date_to,
            filters={
                "normalised_decision": ["Approved"],
                "normalised_application_type": ["full planning application", "householder planning application"]
            }
        )
        
        print(f"Found {len(applications) if isinstance(applications, list) else 0} approved applications\n")
        
        improvements_analysis = []
        total_cost = 0
        total_value_increase = 0
        
        for improvement_type in request.desired_improvements:
            print(f"\n{'─'*70}")
            print(f"Analyzing: {improvement_type.upper()}")
            print(f"{'─'*70}")
            
            keywords = IMPROVEMENT_KEYWORDS.get(improvement_type.lower(), [improvement_type])
            matching_retrofits = []
            decision_times = []
            
            if isinstance(applications, list):
                for app in applications:
                    proposal = app.get("proposal", "").lower()
                    if any(keyword in proposal for keyword in keywords):
                        matching_retrofits.append(app)
                        
                        if app.get("application_date") and app.get("decided_date"):
                            try:
                                app_date = datetime.fromisoformat(app["application_date"].replace('Z', '+00:00'))
                                dec_date = datetime.fromisoformat(app["decided_date"].replace('Z', '+00:00'))
                                days = (dec_date - app_date).days
                                decision_times.append(days)
                            except:
                                pass
            
            avg_time = sum(decision_times) / len(decision_times) if decision_times else None
            approved_count = len(matching_retrofits)
            
            examples = []
            for app in matching_retrofits[:5]:
                decision_time = None
                if app.get("application_date") and app.get("decided_date"):
                    try:
                        app_date = datetime.fromisoformat(app["application_date"].replace('Z', '+00:00'))
                        dec_date = datetime.fromisoformat(app["decided_date"].replace('Z', '+00:00'))
                        decision_time = (dec_date - app_date).days
                    except:
                        pass
                
                examples.append(RetrofitExample(
                    planning_reference=app.get("planning_reference", "N/A"),
                    proposal=app.get("proposal", "N/A"),
                    decision=app.get("normalised_decision", "N/A"),
                    decision_time_days=decision_time,
                    application_date=app.get("application_date", "N/A"),
                    decided_date=app.get("decided_date")
                ))
            
            estimated_cost = ESTIMATED_COSTS.get(improvement_type.lower(), 5000)
            roi_percent = GREEN_PREMIUM.get(improvement_type.lower(), 2.5)
            value_increase = estimated_cost * (roi_percent / 100) * 100
            
            feasibility = "HIGH" if approved_count >= 3 else "MEDIUM" if approved_count >= 1 else "LOW"
            
            print(f"✓ Approved examples: {approved_count}")
            print(f"⏱  Average approval time: {avg_time:.0f} days" if avg_time else "⏱  Average approval time: N/A")
            print(f"💷 Estimated cost: £{estimated_cost:,.2f}")
            print(f"📈 ROI: {roi_percent}% (£{value_increase:,.2f} value increase)")
            print(f"✅ Feasibility: {feasibility}")
            
            improvements_analysis.append(ImprovementAnalysis(
                improvement_type=improvement_type,
                feasibility=feasibility,
                approved_examples=approved_count,
                average_time_days=avg_time,
                estimated_cost=estimated_cost,
                estimated_roi_percent=roi_percent,
                green_premium_value=value_increase,
                examples=examples
            ))
            
            total_cost += estimated_cost
            total_value_increase += value_increase
        
        total_roi = ((total_value_increase / total_cost) * 100) if total_cost > 0 else 0
        
        summary = f"Analysis for {len(request.desired_improvements)} improvements at property {request.property_reference}. "
        summary += f"Total estimated cost: £{total_cost:,.2f}. "
        summary += f"Projected value increase: £{total_value_increase:,.2f} ({total_roi:.1f}% ROI). "
        
        if total_cost <= request.budget:
            summary += f"All improvements fit within budget of £{request.budget:,.2f}. "
        else:
            summary += f"Total cost exceeds budget by £{total_cost - request.budget:,.2f}. "
        
        high_feasibility = sum(1 for imp in improvements_analysis if imp.feasibility == "HIGH")
        if high_feasibility > 0:
            summary += f"{high_feasibility} improvement(s) have high feasibility based on local approvals."
        
        print(f"\n{'='*70}")
        print(f"SUMMARY")
        print(f"{'='*70}")
        print(f"Total Cost: £{total_cost:,.2f}")
        print(f"Total ROI: {total_roi:.1f}%")
        print(f"Value Increase: £{total_value_increase:,.2f}")
        print(f"Within Budget: {'Yes' if total_cost <= request.budget else 'No'}")
        print(f"{'='*70}\n")
        
        return PropertyAnalysisResponse(
            property_reference=request.property_reference,
            location={"latitude": request.latitude, "longitude": request.longitude},
            budget=request.budget,
            improvements=improvements_analysis,
            total_cost=total_cost,
            total_roi_percent=total_roi,
            total_value_increase=total_value_increase,
            summary=summary
        )
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")





if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("   PROPTECH ROI ANALYSIS API - MVP")
    print("   Cost-Benefit Analysis for Energy Efficiency Upgrades")
    print("="*70)
    print("\n🏠 Endpoint: POST /api/analyze")
    print("👀 Docs: http://localhost:8000/docs")
    print("\n" + "="*70 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
