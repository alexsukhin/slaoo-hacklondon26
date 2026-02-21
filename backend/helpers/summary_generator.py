def generate_summary(
    postcode: str,
    num_improvements: int,
    total_cost: float,
    total_value_increase: float,
    total_roi: float,
    budget: float,
    high_feasibility_count: int,
    within_budget: bool
) -> str:
    """
    Generate summary text for the analysis.
    
    TODO:
    - Add LLM-generated insights using Gemini
    - Include neighborhood ranking
    - Add regulatory compliance notes
    - Suggest next steps
    """
    summary = f"Analysis for {num_improvements} improvements at {postcode}. "
    summary += f"Total estimated cost: £{total_cost:,.2f}. "
    summary += f"Projected value increase: £{total_value_increase:,.2f} ({total_roi:.1f}% ROI). "
    
    if within_budget:
        remaining = budget - total_cost
        summary += f"All improvements fit within budget of £{budget:,.2f} (£{remaining:,.2f} remaining). "
    else:
        excess = total_cost - budget
        summary += f"Total cost exceeds budget by £{excess:,.2f}. "
    
    if high_feasibility_count > 0:
        summary += f"{high_feasibility_count} improvement(s) have high feasibility based on local approvals."
    
    return summary
