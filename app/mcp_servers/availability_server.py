from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from app.service.availability_service import get_availability_service

app = FastAPI(
    title="Daily Availability MCP Server",
    description="Manages photographer daily availability and bookings",
    version="2.0.0"
)

class CheckDailyAvailabilityRequest(BaseModel):
    photographer_id: str  
    date: str           

class CheckMultipleDatesRequest(BaseModel):
    photographer_id: str
    dates: List[str]

class CheckMultiplePhotographersRequest(BaseModel):
    photographer_ids: List[str] 
    date: str                  

class GetMonthlyAvailabilityRequest(BaseModel):
    photographer_id: str
    year: int
    month: int

class SetDailyAvailabilityRequest(BaseModel):
    photographer_id: str  
    date: str            
    available: bool
    notes: Optional[str] = None  

class BookDateRequest(BaseModel):
    photographer_id: str
    date: str
    client_id: str
    booking_id: Optional[str] = None    

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "daily-availability", 
        "type": "internal",
        "version": "2.0.0",
        "message": "Daily availability server is running and ready to handle bookings!"
    }

@app.post("/tools/check_daily_availability")
async def check_daily_availability(request: CheckDailyAvailabilityRequest):
    try:
        service = get_availability_service()
        
        result = await service.check_daily_availability(
            photographer_id=request.photographer_id,
            date_str=request.date
        )
        
        return {
            "photographer_id": request.photographer_id,
            "date": request.date,
            **result  
        }
        
    except Exception as e:
        return {
            "error": f"Daily availability check failed: {str(e)}",
            "photographer_id": request.photographer_id,
            "available": False
        }

@app.post("/tools/check_multiple_dates")
async def check_multiple_dates(request: CheckMultipleDatesRequest):
    try:
        service = get_availability_service()
        
        results = await service.check_multiple_dates(
            photographer_id=request.photographer_id,
            dates=request.dates
        )
        
        return {
            "photographer_id": request.photographer_id,
            "dates_checked": len(request.dates),
            "availability": results
        }
        
    except Exception as e:
        return {
            "error": f"Multiple dates check failed: {str(e)}",
            "availability": {}
        }

@app.post("/tools/check_multiple_photographers")
async def check_multiple_photographers(request: CheckMultiplePhotographersRequest):
    try:
        service = get_availability_service()
        
        results = await service.find_available_photographers_daily(
            date_str=request.date,
            photographer_ids=request.photographer_ids
        )
        
        return {
            "date": request.date,
            "photographers_checked": len(request.photographer_ids),
            "available_count": len(results),
            "available_photographers": results
        }
        
    except Exception as e:
        return {
            "error": f"Multiple photographers check failed: {str(e)}",
            "available_photographers": []
        }

@app.post("/tools/get_monthly_availability")
async def get_monthly_availability(request: GetMonthlyAvailabilityRequest):
    try:
        service = get_availability_service()
        
        result = await service.get_monthly_availability(
            photographer_id=request.photographer_id,
            year=request.year,
            month=request.month
        )
        
        return {
            "photographer_id": request.photographer_id,
            "year": request.year,
            "month": request.month,
            **result
        }
        
    except Exception as e:
        return {
            "error": f"Monthly availability check failed: {str(e)}",
            "availability": {}
        }

@app.post("/tools/set_daily_availability")
async def set_daily_availability(request: SetDailyAvailabilityRequest):
    try:
        service = get_availability_service()
        result = await service.set_daily_availability(
            photographer_id=request.photographer_id,
            date_str=request.date,
            available=request.available,
            notes=request.notes
        )
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/tools/book_date")
async def book_date(request: BookDateRequest):
    try:
        service = get_availability_service()
        result = await service.book_date(
            photographer_id=request.photographer_id,
            date_str=request.date,
            client_id=request.client_id,
            booking_id=request.booking_id
        )
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/tools/cancel_booking")
async def cancel_booking(request: BookDateRequest):
    try:
        service = get_availability_service()
        result = await service.cancel_booking(
            photographer_id=request.photographer_id,
            date_str=request.date,
            client_id=request.client_id
        )
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    print("Starting Daily Availability MCP Server on port 8082")
    print("   Daily photographer availability management")
    print("   Features: Daily booking, monthly calendar, multi-photographer search")
    uvicorn.run(app, host="0.0.0.0", port=8082)