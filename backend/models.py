from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date


class PropertySearchRequest(BaseModel):
    uprn: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius: Optional[int] = Field(default=300, description="Search radius in meters")


class PlanningApplicationFilter(BaseModel):
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    application_types: Optional[List[str]] = None
    decisions: Optional[List[str]] = None


class AreaAnalysisRequest(BaseModel):
    latitude: float
    longitude: float
    radius: int = Field(default=500, ge=50, le=2000)
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class RetrofitAnalysisRequest(BaseModel):
    latitude: float
    longitude: float
    improvement_type: str
    radius: int = Field(default=300, ge=50, le=1000)


class PropertyAnalysisResponse(BaseModel):
    property_reference: Optional[str] = None
    planning_applications: List[Dict[str, Any]] = []
    nearby_retrofits: List[Dict[str, Any]] = []
    area_statistics: Optional[Dict[str, Any]] = None
    recommendations: List[str] = []
