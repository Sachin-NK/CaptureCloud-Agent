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

booking_assistant = BookingAssistant(llm)
pricing_agent = PricingPackageAgent(llm)

sessions = {} 

def get_session(session_id: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = {"history": [], "context": {}}
    return sessions[session_id]

def determine_agent(message: str) -> str:
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
        
        if session_id is None:
            import time
            session_id = f"{client_id}_{int(time.time())}"
        
        session_state = get_session(session_id)
        
                                    
        agent_type = determine_agent(message)
        
        if agent_type == "pricing":
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
            response = await booking_assistant.handle_booking_request(
                message=message,
                client_id=client_id,
                session_state=session_state
            )
            response["session_id"] = session_id
        
        session_state["history"].append({"role": "user", "content": message})
        session_state["history"].append({"role": "assistant", "content": response.get("message", "")})
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/booking/create")
async def create_booking_legacy(request: BookingRequest):
 
    try:
        req = request.requirements
                                                                                
        message_parts = ["I'd like to book a photographer"]
        if req.shoot_date:
            message_parts.append(f"for {req.shoot_date}")
        if req.location:
            message_parts.append(f"in {req.location}")
        if (req.budget_min is not None) or (req.budget_max is not None):
            bmin = f"${req.budget_min:.0f}" if req.budget_min is not None else "unspecified"
            bmax = f"${req.budget_max:.0f}" if req.budget_max is not None else "unspecified"
            message_parts.append(f"with a budget between {bmin} and {bmax}")
        if req.additional_notes:
            message_parts.append(f"Notes: {req.additional_notes}")
        message = " ".join(message_parts)
        
        result = await booking_assistant.handle_booking_request(
            message=message,
            client_id=request.client_id
        )
        
                                                            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/booking/workflow")
async def create_booking_workflow(request: WorkflowBookingRequest):

    try:
        from app.service.booking_workflow import get_booking_workflow_service
        
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
    try:
        message = f"I need to reschedule booking {booking_id} to {new_date}"
        result = await booking_assistant.handle_booking_request(
            message=message,
            client_id="system"                               
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/pricing/analyze", response_model=PricingRecommendation)
async def analyze_pricing(request: PricingAnalysisRequest):

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

    try:
        return {
            "location": location,
            "service_type": service_type,
            "analysis": "Market analysis endpoint"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "agent-service",
        "agents": ["booking", "communication", "pricing"]
    }
