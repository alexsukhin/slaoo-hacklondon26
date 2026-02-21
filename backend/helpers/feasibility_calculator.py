def calculate_feasibility(approved_count: int) -> str:
    """
    Calculate feasibility rating based on number of approved examples.
    
    TODO: Consider additional factors:
    - Rejection reasons if any exist
    - Conservation area status
    - Article 4 restrictions
    - Property type matching
    - Distance to examples
    """
    if approved_count >= 3:
        return "HIGH"
    elif approved_count >= 1:
        return "MEDIUM"
    else:
        return "LOW"
