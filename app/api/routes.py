from fastapi import APIRouter, HTTPException
from langchain_openai import ChatOpenAI
from app.config import get_settings
from app.models.schemas import (
    BookingRequest, PricingAnalysisRequest, PricingRecommendation, 
    WorkflowBookingRequest, ChatRequest
)
from app.agents.boockingAssistant import BookingAssistant
from app.agents.pricing_agent import PricingPackageAgent

settings = get_settings()

router = APIRouter()

llm = ChatOpenAI(
    model="gpt-5-nano",
    temperature=0.7,
    openai_api_key=settings.openai_api_key
)

booki=ng_assistant = BookingAssistant()  
pricing_agent = PricingPackageAgent()   

sessions = {} 

def get_session(session_id: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = {"history": [], "context": {}}
    return sessions[session_id]

def determine_agent(message: str) -> str:
    """Simple agent routing logic"""
    pricing_keywords = ["price", "cost", "how much", "pricing", "package", "rate"]
    if any(keyword in message.lower() for keyword in pricing_keywords):
        return "pricing"
    return "booking"


@router.post("/chat")
async def chat_with_assistant(request: ChatRequest):
   
    try:
        message = request.message
        client_id = request.client_id
        session_id = request.session_id
        
        if not message or not client_id:
            raise HTTPException(status_code=400, detail="message and client_id are required")
        
        # Generate session ID if not provided
        if session_id is None:
            import time
            session_id = f"{client_id}_{int(time.time())}"
        
        # Get session state
        session_state = get_session(session_id)
        
        # Route to appropriate agent
        agent_type = determine_agent(message)
        
        if agent_type == "pricing":
            # Handle pricing requests
            try:
                result = await pricing_agent.process_pricing(
                    photographer_id="default",
                    service_type="portrait", 
                    location="New York",
                    duration_hours=2
                )
                response = {
                    "success": True,
                    "type": "pricing_info",
                    "message": f"Based on market analysis, I recommend ${result['suggested_price']:.0f} for this service.",
                    "session_id": session_id
                }
            except Exception as e:
                response = {
                    "success": False,
                    "type": "pricing_error", 
                    "message": "I couldn't analyze pricing right now. Please try again.",
                    "session_id": session_id
                }
        else:
            # Handle booking requests
            response = await BookingAssistant.handle_booking_request(
                message=message,
                client_id=client_id,
                session_state=session_state
            )
            response["session_id"] = session_id
        
        # Add to session history
        session_state["history"].append({"role": "user", "content": message})
        session_state["history"].append({"role": "assistant", "content": response.get("message", "")})
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/booking/create")
async def create_booking_legacy(request: BookingRequest):
   
    try:
        # Convert old format to chat message
        requirements = request.requirements
        message = f"I need a {requirements.get('preferred_style', [''])[0]} photographer"
        if requirements.get('shoot_date'):
            message += f" for {requirements['shoot_date']}"
        if requirements.get('location'):
            message += f" in {requirements['location']}"
        
        result = await BookingAssistant.handle_booking_request(
            message=message,
            client_id=request.client_id
        )
        
        return {
            "success": result.get("success", False),
            "message": result.get("message", ""),
            "session_id": result.get("session_id")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/booking/workflow")
async def create_booking_workflow(request: WorkflowBookingRequest):
    """
    Direct booking through workflow service (for backend integration)
    
    Example:
    {
        "client_id": "client-123",
        "photographer_id": "photographer-456", 
        "package_id": "package-789",
        "requirements": {
            "shoot_date": "2024-12-15",
            "location": "New York",
            "event_type": "wedding"
        }
    }
    """
    try:
        from app.services.booking_workflow import get_booking_workflow_service
        
        workflow_service = get_booking_workflow_service()
        
        result = await workflow_service.process_booking_request(
            client_id=request.client_id,
            photographer_id=request.photographer_id,
            package_id=request.package_id,
            requirements=request.requirements
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/session/{session_id}")
async def get_session_state(session_id: str):
    """Get current conversation session state"""
    try:
        session_state = get_session(session_id)
        return {
            "session_id": session_id,
            "state": session_state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear conversation session state"""
    try:
        if session_id in sessions:
            del sessions[session_id]
        return {
            "success": True,
            "message": f"Session {session_id} cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/booking/reschedule/{booking_id}")
async def reschedule_booking(booking_id: str, new_date: str):
    """Handle booking rescheduling through chat interface"""
    try:
        message = f"I need to reschedule booking {booking_id} to {new_date}"
        result = await BookingAssistant.handle_booking_request(
            message=message,
            client_id="system"  # System-initiated reschedule
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/pricing/analyze", response_model=PricingRecommendation)
async def analyze_pricing(request: PricingAnalysisRequest):
    """ Get dynamic pricing recommendation """
    
    try:
        result = await pricing_agent.process_pricing(
            photographer_id=request.photographer_id,
            service_type=request.service_type,
            location=request.location,
            duration_hours=request.duration_hours,
            season=request.season
        )
        
        comp_prices = result.get("competitor_prices", [])
        
        return PricingRecommendation(
            suggested_price=result.get("suggested_price", 0),
            market_average=result.get("market_data", {}).get("average_price", 0),
            competitive_range={
                "min": min(comp_prices) if comp_prices else 0,
                "max": max(comp_prices) if comp_prices else 0
            },
            reasoning=result.get("reasoning", "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pricing/market-analysis/{location}")
async def get_market_analysis(location: str, service_type: str):
    """
    Get market analysis for a location and service type
    """
    try:
        # This could be expanded to provide detailed market insights
        return {
            "location": location,
            "service_type": service_type,
            "analysis": "Market analysis endpoint"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "agent-service",
        "agents": ["booking", "communication", "pricing"]
    }

@router.get("/test")
async def test_setup():

    from app.agents.test_agent import TestAgent
    
    try:
        agent = TestAgent()
        
        # Test AI
        ai_response = await agent.test_ai("Say hello")
        
        # Test Database
        db_response = await agent.test_database()
        
        return {
            "ai_test": ai_response,
            "db_test": db_response,
            "status": "success"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
