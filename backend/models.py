from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class PropertyAnalysisRequest(BaseModel):
    address: str = Field(description="Full address or postcode")
    property_reference: Optional[str] = Field(default=None, description="UPRN or property reference")
    budget: float = Field(description="Budget in GBP")
    desired_improvements: List[str] = Field(description="solar, insulation, windows, heat_pump")
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class EnergyCompliance(BaseModel):
    current_epc: str
    projected_epc: str
    compliance_status: str
    suggested_improvements: Optional[List[str]] = []
    current_co2_emissions: Optional[float] = None
    potential_co2_emissions: Optional[float] = None
    current_energy_consumption: Optional[float] = None

class RetrofitExample(BaseModel):
    planning_reference: str
    proposal: str
    decision: str
    decision_time_days: Optional[int]
    application_date: str
    decided_date: Optional[str]
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_energy_rating: Optional[str] = None

class ImprovementAnalysis(BaseModel):
    improvement_type: str
    feasibility: str
    approved_examples: int
    average_time_days: Optional[float]
    estimated_cost: float
    estimated_roi_percent: float
    green_premium_value: float
    value_explanation: Optional[str] = None 
    co2_savings_kg: float
    kwh_savings: float
    examples: List[RetrofitExample]

class PropertyAnalysisResponse(BaseModel):
    property_reference: str
    location: Dict[str, float]
    budget: float
    improvements: List[ImprovementAnalysis]
    total_cost: float
    total_roi_percent: float
    total_value_increase: float
    total_co2_savings: float
    total_kwh_savings: float
    summary: str
    energy_compliance: EnergyCompliance

class AddressAnalysisRequest(BaseModel):
    address_query: str
    budget: float
    desired_improvements: List[str]