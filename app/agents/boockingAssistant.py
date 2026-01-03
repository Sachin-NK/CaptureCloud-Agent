import re
from typing import Any, Dict,  Optional, List, TypedDict
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.models.schemas import BookingRequest, PhotographerMatch
import json 
from app.database import get_supabase_agent
from app.service.mcp_client import get_mcp_client

class BookingState(TypedDict):
    message: str                   
    client_id: str                 
    session_state: Dict             
    intent: Dict                   
    matches: List[Dict]             
    response: Dict                  
    current_step: str             

class BookingAssistant:
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.supabase = get_supabase_agent()
        self.mcp = get_mcp_client()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(BookingState)
        
        workflow.add_node("analyze_intent", self.analyze_intent)
        workflow.add_node("process_request", self.process_request) 
        workflow.add_node("finalize_response", self.finalize_response)
        
        workflow.set_entry_point("analyze_intent")
        workflow.add_edge("analyze_intent", "process_request")
        workflow.add_edge("process_request", "finalize_response")
        workflow.add_edge("finalize_response", END)
        
        return workflow.compile()
    
    async def handle_booking_request(self, message: str, client_id: str, session_state: Dict = None) -> Dict[str, Any]:
        
        if session_state is None:
            session_state = {"step": "initial"}
        
        initial_state = BookingState(
            message=message,
            client_id=client_id,
            session_state=session_state,
            intent={},
            matches=[],
            response={},
            current_step="initialized"
        )
        
        final_state = await self.graph.ainvoke(initial_state)
        
        return final_state["response"]
    
    
    async def analyze_intent(self, state: BookingState) -> BookingState:
        
        message = state["message"]
        session_state = state["session_state"]
        current_step = session_state.get("step", "initial")
        
        if current_step == "showing_options":
            state["intent"] = {
                "type": "selection_from_options", 
                "photographer_name": message.strip(),
                "requirements": {}
            }
            state["current_step"] = "intent_analyzed"
            return state
        
        intent_prompt = ChatPromptTemplate.from_messages([
            ("system", """Analyze the booking request to determine intent.
            
            Intent Types:
            1. "direct_booking" - Client mentions specific photographer name
            2. "recommendation_request" - Client wants suggestions  
            3. "unclear" - Intent is not clear
            
            Return JSON: {"type": "...", "photographer_name": "...", "requirements": {...}}"""),
            ("user", "Message: {message}")
        ])
        
        try:
            chain = intent_prompt | self.llm
            response = await chain.ainvoke({"message": message})
            
            json_match = re.search(r'\\{.*\\}', response.content, re.DOTALL)
            if json_match:
                intent = json.loads(json_match.group())
                intent["original_message"] = message
                state["intent"] = intent
            else:
                state["intent"] = {"type": "unclear", "original_message": message}
                
        except Exception as e:
            state["intent"] = {"type": "unclear", "original_message": message}
        
        state["current_step"] = "intent_analyzed"
        return state
    

    
    async def process_request(self, state: BookingState) -> BookingState:
        
        intent = state["intent"]
        intent_type = intent["type"]
        
        if intent_type == "direct_booking" or intent_type == "selection_from_options":
            state = await self._handle_direct_booking_step(state)
        elif intent_type == "recommendation_request":
            state = await self._handle_recommendation_step(state)
        else:
            state = await self._handle_unclear_step(state)
        
        state["current_step"] = "request_processed"
        return state
    
    async def finalize_response(self, state: BookingState) -> BookingState:
        
        state["current_step"] = "completed"
        return state
    
    
    async def _handle_direct_booking_step(self, state: BookingState) -> BookingState:
        
        intent = state["intent"]
        photographer_name = intent.get("photographer_name", "")
        
        matches = await self._find_photographers_by_name(photographer_name)
        state["matches"] = matches
        
        if not matches:
            state["response"] = {
                "success": False,
                "type": "photographer_not_found",
                "message": f"I couldn't find a photographer named '{photographer_name}'. Would you like me to show you available photographers instead?",
                "suggested_action": "show_recommendations"
            }
        elif len(matches) > 1:
            session_state = state["session_state"]
            session_state.update({
                "step": "clarifying_photographer",
                "photographer_matches": matches,
                "original_intent": intent
            })
            
            state["response"] = {
                "success": False,
                "type": "multiple_matches",
                "message": f"I found {len(matches)} photographers named '{photographer_name}'. Which one did you mean?",
                "options": [
                    {
                        "id": match["id"],
                        "name": match["name"],
                        "location": match["location"],
                        "rating": match["rating"],
                        "specialties": match["portfolio_style"]
                    }
                    for match in matches
                ],
                "session_state": session_state
            }
        else:
            photographer = matches[0]
            booking_result = await self._create_booking(photographer, intent.get("requirements", {}), state["client_id"])
            state["response"] = booking_result
        
        return state
    
    async def _handle_recommendation_step(self, state: BookingState) -> BookingState:
        
        intent = state["intent"]
        requirements = intent.get("requirements", {})
        
        recommendations = await self._get_photographer_recommendations(requirements)
        state["matches"] = recommendations
        
        if not recommendations:
            state["response"] = {
                "success": False,
                "type": "no_matches",
                "message": "I couldn't find any photographers matching your requirements. Would you like to adjust your criteria?",
                "suggestions": ["Try different dates", "Expand location", "Adjust budget"]
            }
        else:
            session_state = state["session_state"]
            session_state.update({
                "step": "showing_options",
                "recommendations": recommendations,
                "original_requirements": requirements
            })
            
            state["response"] = {
                "success": True,
                "type": "recommendations",
                "message": f"I found {len(recommendations)} great photographers for you! Here are the top matches:",
                "options": [
                    {
                        "rank": i + 1,
                        "id": rec["id"],
                        "name": rec["name"],
                        "rating": rec["rating"],
                        "specialties": rec["portfolio_style"],
                        "location": rec["location"],
                        "price_range": f"${rec['min_price']} - ${rec['max_price']}",
                        "match_reason": rec.get("match_reason", "Good match for your needs")
                    }
                    for i, rec in enumerate(recommendations[:5])
                ],
                "next_step": "Tell me which photographer you'd like to book (by name or number).",
                "session_state": session_state
            }
        
        return state
    
    async def _handle_unclear_step(self, state: BookingState) -> BookingState:
        
        state["response"] = {
            "success": False,
            "type": "need_clarification",
            "message": "I'd be happy to help you book a photographer! You can either:",
            "options": [
                "Tell me the name of a specific photographer you'd like to book",
                "Describe what kind of photography you need and I'll show you recommendations"
            ],
            "examples": [
                "\"I want to book Sarah Johnson\"",
                "\"I need a wedding photographer for December 15th\""
            ]
        }
        
        return state
    
    
    async def _find_photographers_by_name(self, name: str) -> List[Dict[str, Any]]:
        
        try:
            response = self.supabase.table("photographers").select("""
                id, portfolio_style, location, rating, is_active,
                users!inner (first_name, last_name, email),
                packages (id, name, price, description, is_active)
            """).eq("is_active", True).execute()
            
            photographers = response.data
            matches = []
            name_parts = name.lower().split()
            
            for photographer in photographers:
                user = photographer.get("users", {})
                first_name = user.get("first_name", "").lower()
                last_name = user.get("last_name", "").lower()
                full_name = f"{first_name} {last_name}".strip()
                

                if (name.lower() == full_name or
                    any(part in full_name for part in name_parts) or
                    (len(name_parts) == 1 and name_parts[0] in [first_name, last_name])):
                    
                    active_packages = [pkg for pkg in photographer.get("packages", []) if pkg.get("is_active")]
                    if active_packages:
                        matches.append({
                            "id": photographer["id"],
                            "name": full_name.title(),
                            "email": user.get("email"),
                            "location": photographer.get("location"),
                            "rating": photographer.get("rating", 0),
                            "packages": active_packages,
                            "min_price": min(pkg["price"] for pkg in active_packages),
                            "max_price": max(pkg["price"] for pkg in active_packages)
                        })
            
            return matches
            
        except Exception as e:
            print(f"Error finding photographers: {e}")
            return []
    
    async def _get_photographer_recommendations(self, requirements: Dict) -> List[Dict[str, Any]]:
        
        try:
            response = self.supabase.table("photographers").select("""
                id, portfolio_style, location, rating, is_active,
                users!inner (first_name, last_name, email),
                packages (id, name, price, description, is_active)
            """).eq("is_active", True).execute()
            
            photographers = response.data
            valid_photographers = []
            
            for photographer in photographers:
                user = photographer.get("users", {})
                active_packages = [pkg for pkg in photographer.get("packages", []) if pkg.get("is_active")]
                
                if not active_packages:
                    continue
                
                full_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip().title()
                min_price = min(pkg["price"] for pkg in active_packages)
                max_price = max(pkg["price"] for pkg in active_packages)
                
                valid_photographers.append({
                    "id": photographer["id"],
                    "name": full_name,
                    "email": user.get("email"),
                    "location": photographer.get("location"),
                    "rating": photographer.get("rating", 0),
                    "packages": active_packages,
                    "min_price": min_price,
                    "max_price": max_price,
                    "photographer_data": photographer  
                })
            
            if not valid_photographers:
                return []
            
            all_prices = [p["min_price"] for p in valid_photographers]
            min_price_in_pool = min(all_prices)
            max_price_in_pool = max(all_prices)
            
            scored_photographers = []
            for photographer in valid_photographers:
                score = self._calculate_match_score_with_price_context(
                    photographer["photographer_data"], 
                    requirements,
                    photographer["min_price"],
                    min_price_in_pool,
                    max_price_in_pool
                )
                
                if score > 0:
                    photographer["match_score"] = score
                    photographer["match_reason"] = self._generate_match_reason(
                        photographer["photographer_data"], 
                        requirements, 
                        score,
                        photographer["min_price"],
                        min_price_in_pool
                    )

                    del photographer["photographer_data"]
                    scored_photographers.append(photographer)
            
            scored_photographers.sort(key=lambda x: x["match_score"], reverse=True)
            return scored_photographers[:10]
            
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []
    
    def _calculate_match_score_with_price_context(
        self, 
        photographer: Dict, 
        requirements: Dict, 
        photographer_min_price: float,
        pool_min_price: float,
        pool_max_price: float
    ) -> float:
        
        score = 0.0
        
        rating = photographer.get("rating", 0)
        score += (rating / 5.0) * 60  
        
        if pool_max_price > pool_min_price: 
            price_position = (pool_max_price - photographer_min_price) / (pool_max_price - pool_min_price)
            score += price_position * 10  
        else:
            score += 5  
        
        req_location = requirements.get("location", "").lower()
        photo_location = photographer.get("location", "").lower()
        if req_location and photo_location:
            if req_location in photo_location or photo_location in req_location:
                score += 20  
        
        packages = photographer.get("packages", [])
        if packages:
            score += 10  
        
        return min(score, 100)
    
    def _generate_match_reason(
        self, 
        photographer: Dict, 
        requirements: Dict, 
        score: float,
        photographer_price: float = 0,
        pool_min_price: float = 0
    ) -> str:
        
        reasons = []
        
        if score >= 80:
            reasons.append("Excellent match")
        elif score >= 60:
            reasons.append("Good match")
        else:
            reasons.append("Potential match")
        
        rating = photographer.get("rating", 0)
        if rating >= 4.5:
            reasons.append("highly rated")
        
        if photographer_price > 0 and pool_min_price > 0:
            if photographer_price == pool_min_price:
                reasons.append("lowest price")
            elif photographer_price <= pool_min_price * 1.2:
                reasons.append("great value")
            elif photographer_price <= pool_min_price * 1.5:
                reasons.append("competitive pricing")
        
        req_location = requirements.get("location", "").lower()
        photo_location = photographer.get("location", "").lower()
        if req_location and photo_location:
            if req_location in photo_location or photo_location in req_location:
                reasons.append("local photographer")
        
        return ", ".join(reasons)
    
    async def _create_booking(self, photographer: Dict, requirements: Dict, client_id: str) -> Dict[str, Any]:
        
        packages = photographer.get("packages", [])
        if not packages:
            return {
                "success": False,
                "type": "no_packages",
                "message": f"{photographer['name']} doesn't have any active packages."
            }
        
        selected_package = min(packages, key=lambda x: x["price"])
        
        shoot_date = requirements.get("shoot_date")
        if shoot_date:
            availability_result = await self.mcp.check_availability(
                photographer_id=photographer["id"],
                date=shoot_date
            )
            
            if not availability_result.get("available", True):
                return {
                    "success": False,
                    "type": "not_available",
                    "message": f"{photographer['name']} is not available on {shoot_date}. Would you like to check other dates?",
                    "reason": availability_result.get("reason", "Unavailable")
                }
        
        location = requirements.get("location")
        if location and shoot_date and requirements.get("outdoor", False):
            weather_result = await self.mcp.get_weather_forecast(location, shoot_date)
            
            if not weather_result.get("good_for_outdoor_shoot", True):
                weather_warning = {
                    "weather_warning": True,
                    "weather_info": weather_result,
                    "recommendation": "Consider indoor backup or rescheduling"
                }
            else:
                weather_warning = {
                    "weather_info": weather_result,
                    "weather_status": "Good conditions expected!"
                }
        else:
            weather_warning = {}
        
        booking_request = {
            "client_id": client_id,
            "photographer_id": photographer["id"],
            "package_id": selected_package["id"],
            "requirements": requirements,
            "status": "pending_photographer_approval"
        }
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8080/api/bookings/create",
                    json=booking_request,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    booking_result = response.json()
                    
                    response_data = {
                        "success": True,
                        "type": "booking_created",
                        "message": f"Perfect! I've sent a booking request to {photographer['name']} for the {selected_package['name']} (${selected_package['price']}).",
                        "booking_details": {
                            "booking_id": booking_result.get("id"),
                            "photographer_name": photographer["name"],
                            "package_name": selected_package["name"],
                            "price": selected_package["price"],
                            "status": "pending_photographer_approval"
                        },
                        "next_steps": f"{photographer['name']} will be notified and will respond within 24 hours."
                    }
                    
                    if weather_warning:
                        response_data.update(weather_warning)
                    
                    return response_data
                else:
                    return {
                        "success": False,
                        "type": "backend_error",
                        "message": "I found the photographer but couldn't create the booking. Please try again."
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "type": "connection_error",
                "message": "I found the photographer but couldn't connect to our booking system. Please try again."
            }
    
    async def get_enhanced_recommendations(self, requirements: Dict) -> List[Dict[str, Any]]:
        
        basic_recommendations = await self._get_photographer_recommendations(requirements)
        
        if not basic_recommendations:
            return []
        
        enhanced_recommendations = []
        shoot_date = requirements.get("shoot_date")
        location = requirements.get("location")
        
        for photographer in basic_recommendations:
            enhanced_rec = photographer.copy()
            
            if shoot_date:
                availability = await self.mcp.check_availability(
                    photographer_id=photographer["id"],
                    date=shoot_date
                )
                enhanced_rec["availability"] = availability
                
                if not availability.get("available", True):
                    continue
            
            if location and shoot_date and requirements.get("outdoor", False):
                weather = await self.mcp.get_weather_forecast(location, shoot_date)
                enhanced_rec["weather_forecast"] = weather
                
                if weather.get("good_for_outdoor_shoot", True):
                    enhanced_rec["match_score"] = enhanced_rec.get("match_score", 0) + 5
            
            enhanced_recommendations.append(enhanced_rec)
        
        enhanced_recommendations.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        return enhanced_recommendations
    
    async def research_photography_trends(self, topic: str, location: str = None) -> Dict[str, Any]:
        return await self.mcp.photography_research(
            topic=topic,
            location=location,
            year="2024"
        )
    
    async def find_photo_locations(self, city: str, photo_type: str = "general") -> Dict[str, Any]:
        return await self.mcp.find_photo_locations(city, photo_type)
