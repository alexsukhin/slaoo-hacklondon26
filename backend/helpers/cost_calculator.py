# backend/helpers/cost_calculator.py
from typing import List, Dict, Any, Tuple

# 2025 Industry Benchmark Rates (£ per m2 of floor area)
M2_RATES = {
    "insulation": 110.0, 
    "windows": 65.0,     
    "solar": 85.0,       
    "heat_pump": 150.0   
}

def calculate_cost(
    improvement_type: str,
    matching_applications: List[Dict[str, Any]],
    property_metrics: Dict[str, Any]
) -> Tuple[float, str]:
    """Calculate estimated cost based on actual property metrics."""
    area = property_metrics.get("floor_area", 90.0)
    imp_key = improvement_type.lower()
    
    base_rate = M2_RATES.get(imp_key, 100.0)
    cost = area * base_rate
    
    if imp_key == "heat_pump":
        cost = max(cost - 7500, 4000)

    explanation = f"Calculated for {area}m² at 2025 market rates."
    return round(cost, 2), explanation

# ADD THIS FUNCTION BELOW TO FIX THE IMPORT ERROR
def check_budget(total_cost: float, budget: float) -> Tuple[bool, str]:
    """Check if total cost is within budget and return a message."""
    is_within = total_cost <= budget
    
    if is_within:
        remaining = budget - total_cost
        return True, f"All improvements fit within budget. £{remaining:,.2f} remaining."
    else:
        excess = total_cost - budget
        return False, f"Total cost exceeds budget by £{excess:,.2f}."