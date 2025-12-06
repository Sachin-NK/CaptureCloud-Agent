from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.config import get_settings
import uvicorn

settings = get_settings()

app = FastAPI(
    title= "CaptureCloud Agent Service"
    description= " Ai powered agentic system for CaptureCloud photography mannagement system"
    version= "1.0.0"
)

# settingup CORS Middleware 

app.add_middleware(
    CORSMiddleware,
    allow_originss=[
        "http://localhost:3000",  # frontend
        "http://localhost:8080"   # backend
    ],
    allow_credentials = True
    allow_methods = ["*"],
    allow_headers=["*"],
)

# Include API Routes
app.include_router(
    router,
    prefix="/api/v1/agents",
    tags=["agents"]
)

# Root Endpoint 
@app.get("/")
async def root():
    return{
        "service" : "CaptureCloud Agent",
        "version" : "1.0.0",
        "status" : "running..."
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.service_port
    )