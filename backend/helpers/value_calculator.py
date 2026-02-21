from typing import Optional, Tuple


GREEN_PREMIUM_PERCENTAGES = {
    "solar": 3.5,
    "insulation": 2.8,
    "windows": 2.2,
    "heat_pump": 4.2
}


def calculate_value_increase(
    improvement_type: str,
    estimated_cost: float,
    property_value: Optional[float] = None
) -> Tuple[float, str]:
    """
    Calculate value increase from improvement.
    
    TODO:
    - Join EPC and Price Paid datasets
    - Identify actual increase in price due to EPC improvement
    - Remove general house price inflation to reflect accurate increase due to energy efficiency
    - Use real comparable sales data
    """
    green_premium_percent = GREEN_PREMIUM_PERCENTAGES.get(improvement_type.lower(), 2.5)
    
    if property_value:
        value_increase = property_value * (green_premium_percent / 100)
        explanation = f"Based on {green_premium_percent}% green premium on property value of £{property_value:,.0f}"
    else:
        # Fallback calculation (not accurate without property value)
        value_increase = estimated_cost * (green_premium_percent / 100) * 100
        explanation = f"Estimated {green_premium_percent}% green premium (property value needed for accurate calculation)"
    
    return value_increase, explanation
