import httpx
import asyncio
from typing import Dict, Any, List, Optional
from app.config import get_settings

settings = get_settings()

class MCPClient:
    
    def __init__(self):
        self.base_urls = {
            "availability": "http://localhost:8082",
            "weather": "http://localhost:8084", 
            "search": "http://localhost:8085"
        }
        self.timeout = 10.0
    
    async def _make_request(self, server: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        if server not in self.base_urls:
            return {"error": f"Unknown MCP server: {server}"}
        
        url = f"{self.base_urls[server]}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if data:
                    response = await client.post(url, json=data)
                else:
                    response = await client.get(url)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "error": f"HTTP {response.status_code}",
                        "message": response.text
                    }
                    
        except httpx.TimeoutException:
            return {"error": f"Timeout connecting to {server} server"}
        except Exception as e:
            return {"error": f"Connection failed: {str(e)}"}
    
    async def check_availability(self, photographer_id: str, date: str, duration_hours: int = 2) -> Dict[str, Any]:
        return await self._make_request("availability", "/tools/check_daily_availability", {
            "photographer_id": photographer_id,
            "date": date
        })
    
    async def check_multiple_dates(self, photographer_id: str, dates: List[str]) -> Dict[str, Any]:
        return await self._make_request("availability", "/tools/check_multiple_dates", {
            "photographer_id": photographer_id,
            "dates": dates
        })
    
    async def get_monthly_availability(self, photographer_id: str, year: int, month: int) -> Dict[str, Any]:
        return await self._make_request("availability", "/tools/get_monthly_availability", {
            "photographer_id": photographer_id,
            "year": year,
            "month": month
        })
    
    async def find_available_photographers(self, date: str, photographer_ids: List[str] = None, duration_hours: int = 2) -> Dict[str, Any]:
        data = {"date": date}
        if photographer_ids:
            data["photographer_ids"] = photographer_ids
            
        return await self._make_request("availability", "/tools/check_multiple_photographers", data)
    
    async def set_daily_availability(self, photographer_id: str, date: str, available: bool, notes: str = None) -> Dict[str, Any]:
        return await self._make_request("availability", "/tools/set_daily_availability", {
            "photographer_id": photographer_id,
            "date": date,
            "available": available,
            "notes": notes
        })
    
    async def book_date(self, photographer_id: str, date: str, client_id: str, booking_id: str = None) -> Dict[str, Any]:
        return await self._make_request("availability", "/tools/book_date", {
            "photographer_id": photographer_id,
            "date": date,
            "client_id": client_id,
            "booking_id": booking_id
        })
    
    async def cancel_booking(self, photographer_id: str, date: str, client_id: str) -> Dict[str, Any]:
        return await self._make_request("availability", "/tools/cancel_booking", {
            "photographer_id": photographer_id,
            "date": date,
            "client_id": client_id
        })
    
    async def get_weather_forecast(self, location: str, date: str = "today") -> Dict[str, Any]:
        return await self._make_request("weather", "/tools/get_forecast", {
            "location": location,
            "date": date
        })
    
    async def check_shoot_conditions(self, location: str, shoot_type: str = "outdoor") -> Dict[str, Any]:
        return await self._make_request("weather", "/tools/check_shoot_conditions", {
            "location": location,
            "shoot_type": shoot_type
        })
    
    async def web_search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        return await self._make_request("search", "/tools/web_search", {
            "query": query,
            "num_results": num_results
        })
    
    async def photography_research(self, topic: str, location: str = None, year: str = "2024") -> Dict[str, Any]:
        return await self._make_request("search", "/tools/photography_research", {
            "topic": topic,
            "location": location,
            "year": year
        })
    
    async def find_photo_locations(self, city: str, photo_type: str = "general") -> Dict[str, Any]:
        return await self._make_request("search", "/tools/find_photo_locations", {
            "city": city,
            "photo_type": photo_type
        })
    
    async def research_pricing(self, service_type: str, location: str) -> Dict[str, Any]:
        return await self._make_request("search", "/tools/research_pricing", {
            "service_type": service_type,
            "location": location
        })
    
    async def health_check_all(self) -> Dict[str, Any]:
        results = {}
        
        tasks = []
        for server in self.base_urls.keys():
            tasks.append(self._check_server_health(server))
        
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, server in enumerate(self.base_urls.keys()):
            result = health_results[i]
            if isinstance(result, Exception):
                results[server] = {"status": "error", "error": str(result)}
            else:
                results[server] = result
        
        return results
    
    async def _check_server_health(self, server: str) -> Dict[str, Any]:
        return await self._make_request(server, "/health")


_mcp_client: Optional[MCPClient] = None

def get_mcp_client() -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client