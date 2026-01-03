from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn
import httpx  
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Search MCP Server",
    description="Web search for photography business intelligence",
    version="1.0.0"
)

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
BING_API_KEY = os.getenv("BING_API_KEY")

class WebSearchRequest(BaseModel):
    query: str
    num_results: Optional[int] = 5
    search_type: Optional[str] = "general"

class PhotographySearchRequest(BaseModel):
    topic: str
    location: Optional[str] = None
    year: Optional[str] = "2024"

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "search",
        "serpapi_configured": bool(SERPAPI_API_KEY),
        "bing_configured": bool(BING_API_KEY),
        "version": "1.0.0",
        "message": "Search service ready to find photography insights!"
    }

@app.post("/tools/web_search")
async def web_search(request: WebSearchRequest):
    if not SERPAPI_API_KEY and not BING_API_KEY:
        return {
            "query": request.query,
            "total_results": 3,
            "results": [
                {
                    "title": f"Mock Result 1 for '{request.query}'",
                    "url": "https://example.com/result1",
                    "snippet": "This is a mock search result. Add SERPAPI_API_KEY or BING_API_KEY for real results.",
                    "position": 1
                },
                {
                    "title": f"Mock Result 2 for '{request.query}'",
                    "url": "https://example.com/result2", 
                    "snippet": "Another mock result showing what real search results would look like.",
                    "position": 2
                },
                {
                    "title": f"Mock Result 3 for '{request.query}'",
                    "url": "https://example.com/result3",
                    "snippet": "Configure your search API key to get real web search results.",
                    "position": 3
                }
            ],
            "note": "These are mock results - add SERPAPI_API_KEY for real search"
        }
    
    try:
        if SERPAPI_API_KEY:
            return await _search_with_serpapi(request)
    
            
    except Exception as e:
        return {
            "error": f"Search failed: {str(e)}",
            "query": request.query,
            "results": []
        }

async def _search_with_serpapi(request: WebSearchRequest):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://serpapi.com/search",
            params={
                "q": request.query,
                "api_key": SERPAPI_API_KEY,
                "num": request.num_results,
                "engine": "google"
            }
        )
        
        data = response.json()
        
        results = []
        for i, result in enumerate(data.get("organic_results", [])[:request.num_results]):
            results.append({
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "position": i + 1
            })
        
        return {
            "query": request.query,
            "total_results": len(results),
            "results": results,
            "search_engine": "google"
        }

async def _search_with_bing(request: WebSearchRequest):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.bing.microsoft.com/v7.0/search",
            headers={"Ocp-Apim-Subscription-Key": BING_API_KEY},
            params={
                "q": request.query,
                "count": request.num_results
            }
        )
        
        data = response.json()
        
        results = []
        for i, result in enumerate(data.get("webPages", {}).get("value", [])[:request.num_results]):
            results.append({
                "title": result.get("name", ""),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", ""),
                "position": i + 1
            })
        
        return {
            "query": request.query,
            "total_results": len(results),
            "results": results,
            "search_engine": "bing"
        }

@app.post("/tools/photography_research")
async def photography_research(request: PhotographySearchRequest):
    query_parts = [request.topic]
    
    if request.location:
        query_parts.append(f"in {request.location}")
    
    if request.year:
        query_parts.append(request.year)
    
    if "photography" not in request.topic.lower():
        query_parts.insert(0, "photography")
    
    search_query = " ".join(query_parts)
    
    search_result = await web_search(WebSearchRequest(
        query=search_query,
        num_results=5
    ))
    
    return {
        "topic": request.topic,
        "location": request.location,
        "year": request.year,
        "search_query_used": search_query,
        **search_result
    }

@app.post("/tools/find_photo_locations")
async def find_photo_locations(request: dict):
    city = request.get("city", "")
    photo_type = request.get("photo_type", "general")
    
    search_queries = {
        "wedding": f"best wedding photography locations {city}",
        "portrait": f"best portrait photography spots {city}",
        "landscape": f"scenic photography locations near {city}",
        "urban": f"street photography spots {city}",
        "general": f"best photography locations {city}"
    }
    
    query = search_queries.get(photo_type, search_queries["general"])
    
    search_result = await web_search(WebSearchRequest(
        query=query,
        num_results=6
    ))
    
    return {
        "city": city,
        "photo_type": photo_type,
        "search_query_used": query,
        **search_result
    }

@app.post("/tools/research_pricing")
async def research_pricing(request: dict):
    service_type = request.get("service_type", "")
    location = request.get("location", "")
    
    query = f"{service_type} pricing {location} 2024"
    
    search_result = await web_search(WebSearchRequest(
        query=query,
        num_results=5
    ))
    
    return {
        "service_type": service_type,
        "location": location,
        "search_query_used": query,
        "research_purpose": "pricing_analysis",
        **search_result
    }

if __name__ == "__main__":
    print("Starting Search MCP Server on port 8085")
    print("   Web search for photography business intelligence")
    uvicorn.run(app, host="0.0.0.0", port=8085)