#This file defines the structure of data that flows through our API

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum

class BookingStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"  
    CANCELLED = "cancelled"

class ClientRequirements(BaseModel):
    budget_min: float              
    budget_max: float             
    shoot_date: date               
    location: str                
    additional_notes: Optional[str] = None 

class BookingRequest(BaseModel):
    client_id: str                 
    photographer_id: str          
    requirements: ClientRequirements

class PhotographerMatch(BaseModel):
    photographer_id: str          
    match_score: float
    reasoning: str 
    available: bool

class BookingProposal(BaseModel):
    booking_id: str                 
    photographer_id: str             
    client_id: str                
    proposed_price: float         
    package_details: Dict[str, Any]

class CommunicationRequest(BaseModel):
    client_id: str
    photographer_id: str
    message: str

class PricingAnalysisRequest(BaseModel):
    photographer_id: str
    location: str
    shoot_date: date

class PricingRecommendation(BaseModel):
    recommended_price: float
    market_average: float
    competitive_range:Dict[str, float]
    justification: str