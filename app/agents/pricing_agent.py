from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from app.database import get_supabase_agent
from app.agents.base_agent import BaseAgent
from datetime import datetime
import json
import statistics  

class PricingState(TypedDict):
    photographer_id: str           
    service_type: str               
    location: str                    
    season: str                    
    market_data: dict              
    competitor_prices: List[float]  
    photographer_history: dict      
    suggested_price: float          
    reasoning: str                  
    current_step: str
    
class PricingPackageAgent(BaseAgent):
    
    def __init__(self, llm: ChatOpenAI = None):
        super().__init__()
        
        if llm:
            self.llm = llm
            
        self.graph = self._build_graph()  
        
    def _build_graph(self) -> StateGraph:

        workflow = StateGraph(PricingState)
        
        # Add workflow steps
        workflow.add_node("analyze_market", self.analyze_market)
        workflow.add_node("get_competitor_prices", self.get_competitor_prices)
        workflow.add_node("analyze_photographer_history", self.analyze_photographer_history)
        workflow.add_node("calculate_optimal_price", self.calculate_optimal_price)
        workflow.add_node("generate_recommendation", self.generate_recommendation)
        
        workflow.set_entry_point("analyze_market")  # Start
        workflow.add_edge("analyze_market", "get_competitor_prices")
        workflow.add_edge("get_competitor_prices", "analyze_photographer_history")
        workflow.add_edge("analyze_photographer_history", "calculate_optimal_price")
        workflow.add_edge("calculate_optimal_price", "generate_recommendation")
        workflow.add_edge("generate_recommendation", END)  # Finish
        
        return workflow.compile()
    
    async def analyze_market(self, state: PricingState) -> PricingState:
        
        # Get completed bookings for same service type and location
        response = self.supabase.table("bookings").select(
            "final_price, location, service_type, created_at"
        ).eq("service_type", state["service_type"]).eq(
            "location", state["location"]
        ).eq("status", "completed").execute()
        
        bookings = response.data
        
        # Calculate market statistics if we have data
        if bookings:
            prices = [b["final_price"] for b in bookings if b.get("final_price")]
            state["market_data"] = {
                "average_price": statistics.mean(prices) if prices else 0,  
                "median_price": statistics.median(prices) if prices else 0,  
                "min_price": min(prices) if prices else 0,                   
                "max_price": max(prices) if prices else 0,                   
                "sample_size": len(prices)                                   
            }
        else:
            
            state["market_data"] = {
                "average_price": 0,
                "median_price": 0,
                "min_price": 0,
                "max_price": 0,
                "sample_size": 0
            }
        
        state["current_step"] = "market_analyzed"
        return state
    
    async def get_competitor_prices(self, state: PricingState) -> PricingState:
        
        response = self.supabase.table("photographers").select(
            "id, base_price, hourly_rate, location"
        ).eq("location", state["location"]).execute()
        
        photographers = response.data
        competitor_prices = []
        
        for photographer in photographers:
            if photographer["id"] != state["photographer_id"]:
                base = photographer.get("base_price", 0)
                hourly = photographer.get("hourly_rate", 0)
                estimated = base + (hourly * state["duration_hours"])
                
                if estimated > 0:
                    competitor_prices.append(estimated)
        
        state["competitor_prices"] = competitor_prices
        state["current_step"] = "competitors_analyzed"
        return state
    
    async def analyze_photographer_history(self, state: PricingState) -> PricingState:

        response = self.supabase.table("bookings").select(
            "final_price, rating, duration_hours, created_at"
        ).eq("photographer_id", state["photographer_id"]).eq(
            "status", "completed"
        ).execute()
        
        bookings = response.data
        
        if bookings:
            prices = [b["final_price"] for b in bookings if b.get("final_price")]
            ratings = [b["rating"] for b in bookings if b.get("rating")]
            
            state["photographer_history"] = {
                "average_price": statistics.mean(prices) if prices else 0,
                "average_rating": statistics.mean(ratings) if ratings else 0,
                "total_bookings": len(bookings),
                "recent_bookings": len([b for b in bookings if self._is_recent(b["created_at"])])
            }
        else:
            state["photographer_history"] = {
                "average_price": 0,
                "average_rating": 0,
                "total_bookings": 0,
                "recent_bookings": 0
            }
        
        state["current_step"] = "history_analyzed"
        return state
    
    async def calculate_optimal_price(self, state: PricingState) -> PricingState:
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a pricing optimization expert for photography services.
            Analyze the market data, competitor prices, and photographer history.
            Consider: market rates, competition, photographer experience, seasonal demand.
            Calculate an optimal price that is competitive yet profitable."""),
            ("user", """Service Details:
            - Type: {service_type}
            - Location: {location}
            - Duration: {duration_hours} hours
            - Season: {season}
            
            Market Data: {market_data}
            Competitor Prices: {competitor_prices}
            Photographer History: {photographer_history}
            
            Provide optimal price as a number.""")
        ])
        
        chain = prompt | self.llm
        response = await chain.ainvoke({
            "service_type": state["service_type"],
            "location": state["location"],
            "duration_hours": state["duration_hours"],
            "season": state["season"],
            "market_data": json.dumps(state["market_data"]),
            "competitor_prices": json.dumps(state["competitor_prices"]),
            "photographer_history": json.dumps(state["photographer_history"])
        })
        
        suggested_price = self._extract_price(response.content, state)
        state["suggested_price"] = suggested_price
        state["current_step"] = "price_calculated"
        return state
    
    async def generate_recommendation(self, state: PricingState) -> PricingState:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a pricing consultant. Explain the pricing recommendation.
            Include: market position, competitive analysis, seasonal factors, and strategy.
            Be concise but informative."""),
            ("user", """Suggested Price: ${suggested_price}
            Market Average: ${market_avg}
            Competitor Range: ${comp_min} - ${comp_max}
            
            Explain this pricing recommendation.""")
        ])
        
        chain = prompt | self.llm
        comp_prices = state["competitor_prices"]
        
        response = await chain.ainvoke({
            "suggested_price": state["suggested_price"],
            "market_avg": state["market_data"]["average_price"],
            "comp_min": min(comp_prices) if comp_prices else 0,
            "comp_max": max(comp_prices) if comp_prices else 0
        })
        
        state["reasoning"] = response.content
        state["current_step"] = "completed"
        return state
    
    def _extract_price(self, llm_response: str, state: PricingState) -> float:
        import re
        
        numbers = re.findall(r'\d+\.?\d*', llm_response)
        if numbers:
            price = float(numbers[0])
            # Sanity check
            if 50 <= price <= 10000:
                return price
        
        market_avg = state["market_data"]["average_price"]
        if market_avg > 0:
            return market_avg
        
        return 200.0 * state["duration_hours"]
    
    def _is_recent(self, date_str: str, days: int = 90) -> bool:
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return (datetime.utcnow() - date).days <= days
        except:
            return False
    
    async def process_pricing(self, photographer_id: str, service_type: str, 
                            location: str, duration_hours: int, season: str = None) -> dict:
        if not season:
            month = datetime.now().month
            season = "peak" if month in [5, 6, 7, 8, 9, 10] else "off-peak"
        
        initial_state = PricingState(
            photographer_id=photographer_id,
            service_type=service_type,
            location=location,
            duration_hours=duration_hours,
            season=season,
            market_data={},
            competitor_prices=[],
            photographer_history={},
            suggested_price=0.0,
            reasoning="",
            current_step="initialized"
        )
        
        final_state = await self.graph.ainvoke(initial_state)
        return final_state
