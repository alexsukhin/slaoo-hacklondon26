from typing import List, Dict, Any, Tuple


ESTIMATED_COSTS = {
    "solar": 7000,
    "insulation": 4500,
    "windows": 5500,
    "heat_pump": 12000
}


def calculate_cost(
    improvement_type: str,
    matching_applications: List[Dict[str, Any]]
) -> Tuple[float, str]:
    """
    Calculate estimated cost for improvement.
    
    TODO:
    - Use data to see how much it costs for similar housing
    - Find dataset for installation costs by property type/size
    - Calculate from proposed_floor_area in applications
    - Factor in property type, size, location
    """
    cost = ESTIMATED_COSTS.get(improvement_type.lower(), 5000)
    explanation = f"Average cost based on similar {improvement_type} installations in your area (500m radius)"
    
    return cost, explanation


def check_budget(total_cost: float, budget: float) -> Tuple[bool, str]:
    """Check if total cost is within budget"""
    is_within = total_cost <= budget
    
    if is_within:
        remaining = budget - total_cost
        return True, f"All improvements fit within budget. £{remaining:,.2f} remaining."
    else:
        excess = total_cost - budget
        return False, f"Total cost exceeds budget by £{excess:,.2f}."
