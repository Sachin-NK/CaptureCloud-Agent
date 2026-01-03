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
    budget_min: float = Field(..., description="Minimum budget in USD", example=500.0)              
    budget_max: float = Field(..., description="Maximum budget in USD", example=1500.0)              
    shoot_date: date = Field(..., description="Preferred shoot date", example="2024-12-25")              
    location: str = Field(..., description="Shoot location", example="Central Park, New York")                
    additional_notes: Optional[str] = Field(None, description="Additional requirements or notes", example="Need outdoor portrait session")  

class BookingRequest(BaseModel):
    client_id: str = Field(..., description="Unique client identifier", example="client-123")                    
    requirements: ClientRequirements = Field(..., description="Client requirements for the booking")  

class PhotographerMatch(BaseModel):
    photographer_id: str = Field(..., description="Unique photographer identifier", example="photographer-456")  
    match_score: float = Field(..., description="Match score from 0.0 to 1.0", example=0.85)    
    reasoning: str = Field(..., description="Explanation for the match score", example="High availability and location match")        
    available: bool = Field(..., description="Whether photographer is available", example=True)       

class BookingProposal(BaseModel):
    booking_id: str = Field(..., description="Unique booking identifier", example="booking-789")                  
    photographer_id: str = Field(..., description="Photographer ID", example="photographer-456")            
    client_id: str = Field(..., description="Client ID", example="client-123")                  
    proposed_price: float = Field(..., description="Proposed price in USD", example=1200.0)            
    package_details: Dict[str, Any] = Field(..., description="Package details and inclusions")  

class CommunicationRequest(BaseModel):
    client_id: str = Field(..., description="Client ID", example="client-123")          
    photographer_id: str = Field(..., description="Photographer ID", example="photographer-456")   
    message: str = Field(..., description="Message content", example="I'd like to discuss the shoot details")           

class PricingAnalysisRequest(BaseModel):
    photographer_id: str = Field(..., description="Photographer ID", example="photographer-456")           
    service_type: str = Field(..., description="Type of photography service", example="wedding")              
    location: str = Field(..., description="Service location", example="New York")                  
    season: Optional[str] = Field(None, description="Season for pricing analysis", example="summer")   

class PricingRecommendation(BaseModel):
    suggested_price: float = Field(..., description="Suggested price in USD", example=1200.0)              
    market_average: float = Field(..., description="Market average price in USD", example=1100.0)               
    competitive_range: Dict[str, float] = Field(..., description="Competitive price range", example={"min": 800.0, "max": 1500.0}) 
    reasoning: str = Field(..., description="Reasoning for the price recommendation", example="Based on location and experience level")                     

class WorkflowBookingRequest(BaseModel):
    client_id: str = Field(..., description="Client ID", example="client-123")                     
    photographer_id: str = Field(..., description="Photographer ID", example="photographer-456")               
    package_id: str = Field(..., description="Package ID", example="package-premium")                    
    requirements: Dict[str, Any] = Field(..., description="Detailed requirements", example={"duration": 2, "style": "portrait"})        

class ChatRequest(BaseModel):
    message: str = Field(..., description="User message", example="I need a photographer for my wedding")                        
    client_id: str = Field(..., description="Client ID", example="client-123")                     
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity", example="session-456")

class MCPAvailabilityRequest(BaseModel):
    photographer_id: str = Field(..., description="Photographer ID", example="photographer-123")
    date: str = Field(..., description="Date to check (YYYY-MM-DD)", example="2024-12-25")
    duration_hours: int = Field(2, description="Duration in hours", example=2)

class MCPWeatherRequest(BaseModel):
    location: str = Field(..., description="Location for weather forecast", example="New York")
    date: str = Field("today", description="Date for forecast", example="2024-12-25")

class MCPSearchRequest(BaseModel):
    query: str = Field(..., description="Search query", example="wedding photography trends 2024")
    num_results: int = Field(5, description="Number of results to return", example=5)

class MCPPhotographyResearchRequest(BaseModel):
    topic: str = Field(..., description="Research topic", example="wedding photography trends")
    location: Optional[str] = Field(None, description="Location filter", example="New York")
    year: str = Field("2024", description="Year for research", example="2024")

class MCPLocationRequest(BaseModel):
    city: str = Field(..., description="City to search in", example="New York")
    photo_type: str = Field("general", description="Type of photography", example="wedding")

class EnhancedRecommendationRequest(BaseModel):
    requirements: Dict[str, Any] = Field(..., description="Booking requirements", example={
        "location": "New York",
        "date": "2024-12-25",
        "budget_range": [800, 1500],
        "style": "wedding"
    })

class ChatResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    type: str = Field(..., description="Response type", example="booking_info")
    message: str = Field(..., description="Response message")
    session_id: str = Field(..., description="Session ID")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status", example="healthy")
    service: str = Field(..., description="Service name", example="agent-service")
    agents: List[str] = Field(..., description="Available agents", example=["booking", "pricing"])

class MCPHealthResponse(BaseModel):
    status: str = Field(..., description="Overall MCP status", example="healthy")
    mcp_servers: Dict[str, Any] = Field(..., description="Individual server statuses")
    message: str = Field(..., description="Status message")

class SessionResponse(BaseModel):
    session_id: str = Field(..., description="Session ID")
    state: Dict[str, Any] = Field(..., description="Session state data")

class GenericResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
