"""
MCP CLIENT - Model Context Protocol Integration

Provides standardized access to internal and external services through MCP servers.

Available MCP Servers:
- Availability: Internal photographer availability system
- Weather: Weather forecast data for shoot planning
- Search: Web search for photography research and trends

Usage:
    from app.utils.mcp_client import get_mcp_client
    
    mcp = get_mcp_client()
    
    # Check photographer availability
    availability = await mcp.call_tool("availability", "check_availability", {
        "photographer_id": "photographer-123",
        "date": "2024-12-15",
        "duration_hours": 2
    })
    
    # Find available photographers
    photographers = await mcp.call_tool("availability", "check_multiple_availability", {
        "photographer_ids": ["123", "456", "789"],
        "date": "2024-12-15"
    })
    
    # Get weather forecast
    weather = await mcp.call_tool("weather", "get_forecast", {
        "location": "New York",
        "date": "2024-12-10"
    })
"""

import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP Client for connecting to external tool servers
    
    Provides standardized interface to:
    - Calendar services (Google Calendar, Outlook)
    - Weather APIs (OpenWeather, Weather.com)
    - Maps services (Google Maps, Mapbox)
    - Email services (SendGrid, AWS SES)
    """
    
    def __init__(self):
        """Initialize MCP client with server configurations"""
        self.servers = {
            "availability": {
                "url": os.getenv("MCP_AVAILABILITY_URL", "http://localhost:8081"),
                "enabled": os.getenv("MCP_AVAILABILITY_ENABLED", "true").lower() == "true"
            },
            "weather": {
                "url": os.getenv("MCP_WEATHER_URL", "http://localhost:8082"),
                "enabled": os.getenv("MCP_WEATHER_ENABLED", "true").lower() == "true"
            },
            "maps": {
                "url": os.getenv("MCP_MAPS_URL", "http://localhost:8083"),
                "enabled": os.getenv("MCP_MAPS_ENABLED", "true").lower() == "true"
            },

            "weather": {
                "url": os.getenv("MCP_WEATHER_URL", "http://localhost:8082"),
                "enabled": os.getenv("MCP_WEATHER_ENABLED", "true").lower() == "true"
            },
            "search": {
                "url": os.getenv("MCP_SEARCH_URL", "http://localhost:8083"),
                "enabled": os.getenv("MCP_SEARCH_ENABLED", "true").lower() == "true"
            }
        }
        
        self.timeout = float(os.getenv("MCP_TIMEOUT", "10.0"))
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    async def call_tool(
        self,
        server: str,
        tool: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call a tool on an MCP server
        
        Parameters:
        - server: Server name (calendar, weather, maps, email)
        - tool: Tool/function name
        - params: Tool parameters
        
        Returns:
        - Tool response as dictionary
        """
        if server not in self.servers:
            raise ValueError(f"Unknown MCP server: {server}")
        
        server_config = self.servers[server]
        
        if not server_config["enabled"]:
            logger.warning(f"MCP server '{server}' is disabled")
            return {"error": f"Server {server} is disabled", "fallback": True}
        
        try:
            url = f"{server_config['url']}/tools/{tool}"
            
            response = await self.client.post(
                url,
                json=params,
                headers={"Content-Type": "application/json"}
            )
            
            response.raise_for_status()
            return response.json()
            
        except httpx.TimeoutException:
            logger.error(f"MCP server '{server}' timeout")
            return {"error": "Timeout", "fallback": True}
            
        except httpx.HTTPError as e:
            logger.error(f"MCP server '{server}' error: {str(e)}")
            return {"error": str(e), "fallback": True}
        
        except Exception as e:
            logger.error(f"Unexpected error calling MCP server '{server}': {str(e)}")
            return {"error": str(e), "fallback": True}
    
    async def get_available_tools(self, server: str) -> List[str]:
        """
        Get list of available tools from a server
        
        Parameters:
        - server: Server name
        
        Returns:
        - List of tool names
        """
        if server not in self.servers:
            return []
        
        server_config = self.servers[server]
        
        if not server_config["enabled"]:
            return []
        
        try:
            url = f"{server_config['url']}/tools"
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("tools", [])
            
        except Exception as e:
            logger.error(f"Failed to get tools from '{server}': {str(e)}")
            return []
    
    async def health_check(self, server: Optional[str] = None) -> Dict[str, bool]:
        """
        Check health status of MCP servers
        
        Parameters:
        - server: Specific server to check, or None for all
        
        Returns:
        - Dictionary of server: healthy status
        """
        servers_to_check = [server] if server else list(self.servers.keys())
        health_status = {}
        
        for srv in servers_to_check:
            if srv not in self.servers:
                continue
            
            server_config = self.servers[srv]
            
            if not server_config["enabled"]:
                health_status[srv] = False
                continue
            
            try:
                url = f"{server_config['url']}/health"
                response = await self.client.get(url, timeout=5.0)
                health_status[srv] = response.status_code == 200
            except:
                health_status[srv] = False
        
        return health_status
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    # ===== AVAILABILITY TOOLS =====
    
    async def check_photographer_availability(
        self,
        photographer_id: str,
        date: str,
        duration_hours: int = 2
    ) -> Dict[str, Any]:
        """
        Check photographer availability for a specific date
        
        Parameters:
        - photographer_id: UUID of the photographer
        - date: Date to check (YYYY-MM-DD)
        - duration_hours: Required duration in hours
        
        Returns:
        - Availability status and available slots with pricing
        """
        return await self.call_tool("availability", "check_availability", {
            "photographer_id": photographer_id,
            "date": date,
            "duration_hours": duration_hours
        })
    
    async def find_available_photographers(
        self,
        date: str,
        duration_hours: int = 2,
        photographer_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Find all available photographers for a specific date
        
        Parameters:
        - date: Date to check (YYYY-MM-DD)
        - duration_hours: Required duration in hours
        - photographer_ids: Optional list of specific photographers to check
        
        Returns:
        - List of available photographers with their slots and pricing
        """
        return await self.call_tool("availability", "check_multiple_availability", {
            "photographer_ids": photographer_ids or [],
            "date": date,
            "duration_hours": duration_hours
        })
    
    # ===== WEATHER TOOLS =====
    
    async def get_weather_forecast(
        self,
        location: str,
        date: str = "today"
    ) -> Dict[str, Any]:
        """
        Get weather forecast for photography planning
        
        Parameters:
        - location: Location name (e.g., "Central Park, New York")
        - date: Date for forecast (YYYY-MM-DD format)
        
        Returns:
        - Weather conditions, temperature, and photography recommendations
        """
        return await self.call_tool("weather", "get_forecast", {
            "location": location,
            "date": date
        })
    
    async def check_shoot_conditions(
        self,
        location: str,
        shoot_type: str = "outdoor"
    ) -> Dict[str, Any]:
        """
        Check weather conditions for specific type of photography
        
        Parameters:
        - location: Where the shoot will be
        - shoot_type: Type of shoot (outdoor, wedding, portrait, landscape)
        
        Returns:
        - Weather suitability and specific recommendations for the shoot type
        """
        return await self.call_tool("weather", "check_shoot_conditions", {
            "location": location,
            "shoot_type": shoot_type
        })

    # ===== SEARCH TOOLS =====
    
    async def web_search(
        self,
        query: str,
        num_results: int = 5
    ) -> Dict[str, Any]:
        """
        Search the web for information
        
        Parameters:
        - query: What to search for
        - num_results: How many results to return
        
        Returns:
        - List of search results with titles, URLs, and descriptions
        """
        return await self.call_tool("search", "web_search", {
            "query": query,
            "num_results": num_results
        })
    
    async def research_photography_topic(
        self,
        topic: str,
        location: Optional[str] = None,
        year: str = "2024"
    ) -> Dict[str, Any]:
        """
        Research photography-specific topics and trends
        
        Parameters:
        - topic: Photography topic (e.g., "wedding photography trends")
        - location: Optional location context
        - year: Year for current trends
        
        Returns:
        - Relevant search results for photography research
        """
        return await self.call_tool("search", "photography_research", {
            "topic": topic,
            "location": location,
            "year": year
        })
    
    async def find_photo_locations(
        self,
        city: str,
        photo_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Find great photography locations in a city
        
        Parameters:
        - city: City to search in
        - photo_type: Type of photography (wedding, portrait, landscape, urban)
        
        Returns:
        - List of recommended photography locations
        """
        return await self.call_tool("search", "find_photo_locations", {
            "city": city,
            "photo_type": photo_type
        })

    # ===== WEATHER TOOLS (CONTINUED) =====
    
    async def get_weather_forecast(
        self,
        location: str,
        date: str
    ) -> Dict[str, Any]:
        """
        Get weather forecast for a location and date
        
        Parameters:
        - location: Location name or coordinates
        - date: Date for forecast (YYYY-MM-DD)
        
        Returns:
        - Weather forecast data
        """
        return await self.call_tool("weather", "get_forecast", {
            "location": location,
            "date": date
        })
    
    async def get_current_weather(self, location: str) -> Dict[str, Any]:
        """
        Get current weather for a location
        
        Parameters:
        - location: Location name or coordinates
        
        Returns:
        - Current weather data
        """
        return await self.call_tool("weather", "get_current", {
            "location": location
        })
    
    # ===== MAPS TOOLS =====
    
    async def get_directions(
        self,
        origin: str,
        destination: str,
        mode: str = "driving"
    ) -> Dict[str, Any]:
        """
        Get directions between two locations
        
        Parameters:
        - origin: Starting location
        - destination: Destination location
        - mode: Travel mode (driving, walking, transit)
        
        Returns:
        - Directions and travel time
        """
        return await self.call_tool("maps", "get_directions", {
            "origin": origin,
            "destination": destination,
            "mode": mode
        })
    
    async def geocode_address(self, address: str) -> Dict[str, Any]:
        """
        Convert address to coordinates
        
        Parameters:
        - address: Address string
        
        Returns:
        - Latitude and longitude
        """
        return await self.call_tool("maps", "geocode", {
            "address": address
        })
    
    # ===== EMAIL TOOLS =====
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send email via MCP email server
        
        Parameters:
        - to: Recipient email
        - subject: Email subject
        - body: Plain text body
        - html: Optional HTML body
        
        Returns:
        - Send status
        """
        return await self.call_tool("email", "send", {
            "to": to,
            "subject": subject,
            "body": body,
            "html": html
        })
    
    async def send_template_email(
        self,
        to: str,
        template: str,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send email using a template
        
        Parameters:
        - to: Recipient email
        - template: Template name
        - variables: Template variables
        
        Returns:
        - Send status
        """
        return await self.call_tool("email", "send_template", {
            "to": to,
            "template": template,
            "variables": variables
        })
    
    # ===== SEARCH TOOLS =====
    
    async def web_search(
        self,
        query: str,
        num_results: int = 5
    ) -> Dict[str, Any]:
        """
        Search the web for information
        
        Parameters:
        - query: Search query
        - num_results: Number of results to return
        
        Returns:
        - Search results with titles, URLs, and snippets
        """
        return await self.call_tool("search", "web_search", {
            "query": query,
            "num_results": num_results
        })
    
    async def search_images(
        self,
        query: str,
        num_results: int = 5
    ) -> Dict[str, Any]:
        """
        Search for images
        
        Parameters:
        - query: Search query
        - num_results: Number of results to return
        
        Returns:
        - Image search results with URLs and metadata
        """
        return await self.call_tool("search", "search_images", {
            "query": query,
            "num_results": num_results
        })
    
    async def search_news(
        self,
        query: str,
        num_results: int = 5
    ) -> Dict[str, Any]:
        """
        Search for news articles
        
        Parameters:
        - query: Search query
        - num_results: Number of results to return
        
        Returns:
        - News articles with titles, sources, and dates
        """
        return await self.call_tool("search", "search_news", {
            "query": query,
            "num_results": num_results
        })
    
    async def get_page_content(
        self,
        url: str
    ) -> Dict[str, Any]:
        """
        Get content from a web page
        
        Parameters:
        - url: URL to fetch
        
        Returns:
        - Page content (text, title, metadata)
        """
        return await self.call_tool("search", "get_page_content", {
            "url": url
        })


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """
    Get or create the global MCP client instance
    
    Returns:
    - MCPClient instance
    """
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


async def close_mcp_client():
    """Close the global MCP client"""
    global _mcp_client
    if _mcp_client is not None:
        await _mcp_client.close()
        _mcp_client = None
