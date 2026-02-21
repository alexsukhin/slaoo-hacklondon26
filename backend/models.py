from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class PropertyAnalysisRequest(BaseModel):
    property_reference: str = Field(description="UPRN or property reference")
    budget: float = Field(description="Budget in GBP")
    desired_improvements: List[str] = Field(
        description="solar, insulation, windows, heat_pump"
    )
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class RetrofitExample(BaseModel):
    planning_reference: str
    proposal: str
    decision: str
    decision_time_days: Optional[int]
    application_date: str
    decided_date: Optional[str]


class ImprovementAnalysis(BaseModel):
    improvement_type: str
    feasibility: str
    approved_examples: int
    average_time_days: Optional[float]
    estimated_cost: float
    estimated_roi_percent: float
    green_premium_value: float
    value_explanation: Optional[str] = None 
    examples: List[RetrofitExample]

class PropertyAnalysisResponse(BaseModel):
    property_reference: str
    location: Dict[str, float]
    budget: float
    improvements: List[ImprovementAnalysis]
    total_cost: float
    total_roi_percent: float
    total_value_increase: float
    summary: str
