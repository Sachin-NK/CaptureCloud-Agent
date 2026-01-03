import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.config import get_settings
import uvicorn

settings = get_settings()

app = FastAPI(
    title="CaptureCloud Agent Service API",
    description="AI-Powered Photography Booking System",
    version="1.0.0",
    contact={
        "name": "CaptureCloud Team",
        "email": "snkodikara52@gmail.com",
    },
    servers=[
        {
            "url": "http://localhost:8081",
            "description": "Development server"
        },
        {
            "url": "https://api.capturecloud.com",
            "description": "Production server"
        }
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:8081",
        "http://localhost:8082",
        "http://localhost:8084",
        "http://localhost:8085",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    router,
    prefix="/api/v1/agents",
    tags=["agents"]
)

@app.get("/", 
         summary="API Root",
         description="Welcome endpoint with service information",
         response_description="Service information and status")
async def root():
    return{
        "service" : "CaptureCloud Agent Service",
        "version" : "1.0.0",
        "status" : "running",
        "description": "AI-powered photography booking system",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "mcp_servers": {
            "availability": "http://localhost:8082",
            "weather": "http://localhost:8084", 
            "search": "http://localhost:8085"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.service_port
    )