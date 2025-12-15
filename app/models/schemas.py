from pydantic import BaseModel, Field  
from typing import Optional, List, Dict, Any 
from datetime import datetime, date  
from enum import Enum  

class BookingStatus(str, Enum):
    PENDING = "pending"       
    CONFIRMED = "confirmed"    
    CANCELLED = "cancelled"   
    COMPLETED = "completed" 

class ClientRequirements(BaseModel):
 
    budget_min: float              
    budget_max: float              
    shoot_date: date              
    location: str                
    additional_notes: Optional[str] = None  

class BookingRequest(BaseModel):

    client_id: str                    
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
    service_type: str              
    location: str                  
    duration_hours: int           
    season: Optional[str] = None   

class PricingRecommendation(BaseModel):
   
    suggested_price: float              
    market_average: float               
    competitive_range: Dict[str, float] 
    reasoning: str                     

class WorkflowBookingRequest(BaseModel):
   
    client_id: str                     
    photographer_id: str               
    package_id: str                    
    requirements: Dict[str, Any]        

class ChatRequest(BaseModel):
    message: str                        
    client_id: str                     
    session_id: Optional[str] = None   
