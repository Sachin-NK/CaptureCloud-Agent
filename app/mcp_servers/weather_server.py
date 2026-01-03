from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Weather MCP Server",
    description="Weather forecasts for photography shoot planning",
    version="1.0.0"
)

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

class GetForecastRequest(BaseModel):
    location: str
    date: str

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "weather",
        "api_configured": bool(OPENWEATHER_API_KEY),
        "version": "1.0.0",
        "message": "Weather service ready to help plan your shoots!"
    }

@app.post("/tools/get_forecast")
async def get_forecast(request: GetForecastRequest):
    
    if not OPENWEATHER_API_KEY:
        return {
            "location": request.location,
            "date": request.date,
            "condition": "Clear",
            "temperature": {"high": 75, "low": 65, "unit": "F"},
            "precipitation": 10,
            "humidity": 45,
            "wind": {"speed": 5, "direction": "NW"},
            "good_for_outdoor_shoot": True,
            "photography_tips": "Perfect weather for outdoor photography!",
            "note": "This is mock data - add OPENWEATHER_API_KEY for real forecasts"
        }
    
    try:
        async with httpx.AsyncClient() as client:
            geo_response = await client.get(
                "http://api.openweathermap.org/geo/1.0/direct",
                params={
                    "q": request.location,
                    "limit": 1,
                    "appid": OPENWEATHER_API_KEY
                }
            )
            
            if not geo_response.json():
                return {
                    "error": f"Location '{request.location}' not found",
                    "suggestion": "Try a more specific location like 'New York, NY' or 'London, UK'"
                }
            
            geo_data = geo_response.json()[0]
            lat, lon = geo_data["lat"], geo_data["lon"]
            
            weather_response = await client.get(
                "https://api.openweathermap.org/data/2.5/forecast",
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": OPENWEATHER_API_KEY,
                    "units": "imperial"
                }
            )
            
            weather_data = weather_response.json()
            
            forecast = weather_data["list"][0]
            condition = forecast["weather"][0]["main"]
            
            good_conditions = ["Clear", "Clouds"]
            is_good_for_shoot = condition in good_conditions and forecast.get("pop", 0) < 0.3
            
            tips = {
                "Clear": "Perfect for outdoor shoots! Great natural lighting.",
                "Clouds": "Excellent for portraits - clouds act as natural softbox!",
                "Rain": "Consider indoor locations or covered areas.",
                "Snow": "Beautiful for winter shoots, but protect equipment!",
                "Thunderstorm": "Definitely move indoors for safety."
            }.get(condition, "Check conditions before shooting.")
            
            return {
                "location": request.location,
                "date": request.date,
                "condition": condition,
                "temperature": {
                    "high": int(forecast["main"]["temp_max"]),
                    "low": int(forecast["main"]["temp_min"]),
                    "current": int(forecast["main"]["temp"]),
                    "unit": "F"
                },
                "precipitation": int(forecast.get("pop", 0) * 100),
                "humidity": forecast["main"]["humidity"],
                "wind": {
                    "speed": int(forecast["wind"]["speed"]),
                    "direction": "Variable"
                },
                "description": forecast["weather"][0]["description"],
                "good_for_outdoor_shoot": is_good_for_shoot,
                "photography_tips": tips
            }
    
    except Exception as e:
        return {
            "error": f"Weather service error: {str(e)}",
            "location": request.location,
            "date": request.date,
            "fallback_advice": "Check local weather apps before outdoor shoots"
        }

@app.post("/tools/check_shoot_conditions")
async def check_shoot_conditions(request: dict):
    
    location = request.get("location", "")
    shoot_type = request.get("shoot_type", "outdoor")
    
    forecast_result = await get_forecast(GetForecastRequest(location=location, date="today"))
    
    if "error" in forecast_result:
        return forecast_result
    
    shoot_advice = {
        "wedding": {
            "good_conditions": ["Clear", "Clouds"],
            "advice": "Wedding shoots need reliable weather. Consider backup indoor venue."
        },
        "portrait": {
            "good_conditions": ["Clouds", "Clear"],
            "advice": "Overcast skies provide beautiful soft lighting for portraits!"
        },
        "landscape": {
            "good_conditions": ["Clear", "Clouds", "Rain"],
            "advice": "Dramatic weather can create stunning landscape photos."
        },
        "outdoor": {
            "good_conditions": ["Clear", "Clouds"],
            "advice": "General outdoor photography works best in stable conditions."
        }
    }
    
    shoot_info = shoot_advice.get(shoot_type, shoot_advice["outdoor"])
    condition = forecast_result.get("condition", "Unknown")
    
    return {
        **forecast_result,
        "shoot_type": shoot_type,
        "recommended": condition in shoot_info["good_conditions"],
        "shoot_specific_advice": shoot_info["advice"]
    }

if __name__ == "__main__":
    print("Starting Weather MCP Server on port 8084")
    print("   Weather forecasts for photography planning")
    uvicorn.run(app, host="0.0.0.0", port=8084)