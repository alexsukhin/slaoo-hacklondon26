from typing import Dict, Any, Tuple

# 2025 Benchmarks: Estimated Annual Impacts (Financial, Energy, Carbon)
ANNUAL_IMPACT_BENCHMARKS = {
    "solar": {"money": 1100.0, "kwh": 3500.0, "co2_kg": 850.0},
    "insulation": {"money": 450.0, "kwh": 2800.0, "co2_kg": 600.0},
    "windows": {"money": 180.0, "kwh": 1200.0, "co2_kg": 250.0},
    "heat_pump": {"money": 650.0, "kwh": 4000.0, "co2_kg": 1500.0}
}

SYSTEM_LIFESPAN = {
    "solar": 25,
    "insulation": 40,
    "windows": 20,
    "heat_pump": 15
}

def get_environmental_impact(improvement_type: str) -> Tuple[float, float]:
    """Returns estimated annual CO2 savings (kg) and Energy savings (kWh)."""
    imp_key = improvement_type.lower()
    impact = ANNUAL_IMPACT_BENCHMARKS.get(imp_key, {"co2_kg": 0.0, "kwh": 0.0})
    return impact["co2_kg"], impact["kwh"]

def calculate_roi_proper(
    improvement_type: str,
    estimated_cost: float,
    value_increase: float,
    analysis_period_years: int = 10
) -> Dict[str, Any]:
    imp_key = improvement_type.lower()
    annual_savings = ANNUAL_IMPACT_BENCHMARKS.get(imp_key, {"money": 200.0})["money"]
    
    total_savings = annual_savings * analysis_period_years
    total_maintenance = (estimated_cost * 0.01) * analysis_period_years
    total_benefit = value_increase + total_savings - total_maintenance
    
    if estimated_cost <= 0:
        return {"roi_percent": 0, "payback_years": 0}
        
    roi_percent = ((total_benefit - estimated_cost) / estimated_cost) * 100
    payback_years = estimated_cost / annual_savings if annual_savings > 0 else 99
    
    return {
        "roi_percent": round(roi_percent, 2),
        "payback_years": round(payback_years, 1),
        "total_savings_10yr": round(total_savings, 2),
        "annual_savings": annual_savings
    }

def calculate_roi(estimated_cost: float, value_increase: float) -> float:
    if estimated_cost == 0:
        return 0
    return ((value_increase - estimated_cost) / estimated_cost) * 100