def calculate_roi(estimated_cost: float, value_increase: float) -> float:
    """
    Calculate ROI percentage.
    
    Formula: (Value Increase - Cost) / Cost * 100
    
    TODO:
    - Include energy savings over time
    - Include maintenance costs
    - Include financing costs if borrowed
    - Calculate payback period
    """
    if estimated_cost == 0:
        return 0
    
    roi = ((value_increase - estimated_cost) / estimated_cost) * 100
    
    return roi
