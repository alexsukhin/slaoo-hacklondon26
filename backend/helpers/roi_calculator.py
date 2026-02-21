from typing import Dict, Any, Tuple # Added Any and Tuple to imports

# 2025 Benchmarks: Estimated Annual Energy Savings
# Based on typical 3-bed semi-detached gas-heated home
ANNUAL_SAVINGS_BENCHMARKS = {
    "solar": 1100.0,      # Savings + Smart Export Guarantee (SEG)
    "insulation": 450.0,  # Based on external wall insulation
    "windows": 180.0,     # Double glazing savings
    "heat_pump": 650.0    # Savings vs. old gas boiler
}

# Lifespan in years for total value calculation
SYSTEM_LIFESPAN = {
    "solar": 25,
    "insulation": 40,
    "windows": 20,
    "heat_pump": 15
}

def calculate_roi_proper(
    improvement_type: str,
    estimated_cost: float,
    value_increase: float,
    analysis_period_years: int = 10
) -> Dict[str, Any]:
    """
    Advanced ROI Calculation incorporating capital growth and operational savings.
    """
    imp_key = improvement_type.lower()
    annual_savings = ANNUAL_SAVINGS_BENCHMARKS.get(imp_key, 200.0)
    
    # 1. Calculate Total Savings over the analysis period (e.g., 10 years)
    total_savings = annual_savings * analysis_period_years
    
    # 2. Subtract Maintenance Costs (Estimated at 1% of cost annually)
    total_maintenance = (estimated_cost * 0.01) * analysis_period_years
    
    # 3. Total Benefit = Capital Value Increase + Energy Savings - Maintenance
    total_benefit = value_increase + total_savings - total_maintenance
    
    # 4. ROI Percentage: (Total Benefit - Cost) / Cost * 100
    if estimated_cost <= 0:
        return {"roi_percent": 0, "payback_years": 0}
        
    roi_percent = ((total_benefit - estimated_cost) / estimated_cost) * 100
    
    # 5. Payback Period (Years to recover initial capital from savings alone)
    payback_years = estimated_cost / annual_savings if annual_savings > 0 else 99
    
    return {
        "roi_percent": round(roi_percent, 2),
        "payback_years": round(payback_years, 1),
        "total_savings_10yr": round(total_savings, 2),
        "annual_savings": annual_savings
    }

# Failsafe for original import in main.py
def calculate_roi(estimated_cost: float, value_increase: float) -> float:
    if estimated_cost == 0:
        return 0
    return ((value_increase - estimated_cost) / estimated_cost) * 100