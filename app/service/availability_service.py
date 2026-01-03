
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from app.database import get_supabase_agent


class AvailabilityService:
    
    def __init__(self):
        self.db = None
    
    async def get_db(self):
        if not self.db:
                                                                
            self.db = get_supabase_agent()
        return self.db
    
    async def check_availability(
        self, 
        photographer_id: str, 
        date_str: str
    ) -> Dict[str, Any]:
        db = await self.get_db()
        
        try:
                                                                                             
            if not db:
                return {
                    "available": True,
                    "reason": "Database not configured; assuming available"
                }
                                                        
            photographer_result = db.table("photographers").select("id, is_active").eq(
                "id", photographer_id
            ).execute()
            
            if not photographer_result.data:
                return {
                    "available": False,
                    "reason": "Photographer not found"
                }
            
            photographer = photographer_result.data[0]
            if not photographer.get("is_active", False):
                return {
                    "available": False,
                    "reason": "Photographer is not active"
                }
            
                                          
            try:
                check_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if check_date < date.today():
                    return {
                        "available": False,
                        "reason": "Date is in the past"
                    }
            except ValueError:
                return {
                    "available": False,
                    "reason": "Invalid date format"
                }
            
                                                                          
                                                                       
                                                                       
            
            return {
                "available": True,
                "reason": "Photographer is available on this date"
            }
            
        except Exception as e:
            return {
                "available": False,
                "reason": f"Error checking availability: {str(e)}"
            }
    
    async def find_available_photographers(
        self, 
        date_str: str,
        photographer_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        db = await self.get_db()
        
                                       
        if photographer_ids is None:
                                          
            photographers_result = db.table("photographers").select("id").eq(
                "is_active", True
            ).execute()
            photographer_ids = [p["id"] for p in photographers_result.data]
        
                                                  
        results = []
        for photographer_id in photographer_ids:
            availability = await self.check_availability(photographer_id, date_str)
            results.append({
                "photographer_id": photographer_id,
                **availability
            })
        
                                             
        return [r for r in results if r["available"]]


                         
_availability_service: Optional[AvailabilityService] = None

def get_availability_service() -> AvailabilityService:
    global _availability_service
    if _availability_service is None:
        _availability_service = AvailabilityService()
    return _availability_service

                        
def get_booking_service() -> AvailabilityService:
    return get_availability_service()