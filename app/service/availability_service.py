"""
Simple Availability Service
===========================
Basic availability checking for AI agents.
No time slots - just simple date availability.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from app.database import get_supabase_agent


class AvailabilityService:
    """
    Simple availability checking for AI agents
    
    Features:
    - Check if photographer is available on a date
    - Find available photographers
    
    Note: No time slots - photography sessions have flexible duration
    """
    
    def __init__(self):
        self.db = None
    
    async def get_db(self):
        """Get database connection"""
        if not self.db:
            self.db = await get_supabase_agent()
        return self.db
    
    async def check_availability(
        self, 
        photographer_id: str, 
        date_str: str
    ) -> Dict[str, Any]:
        """
        Check if photographer is available on a specific date
        
        Args:
            photographer_id: UUID of photographer
            date_str: Date in YYYY-MM-DD format
        
        Returns:
            {
                "available": bool,
                "reason": "Optional explanation if not available"
            }
        """
        db = await self.get_db()
        
        try:
            # Check if photographer exists and is active
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
            
            # Check if date is in the past
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
            
            # Check if photographer has any existing bookings on this date
            # This would check against the Java backend's Project table
            # For now, assume available (backend will handle conflicts)
            
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
        """
        Find photographers available on a specific date
        
        Args:
            date_str: "2024-12-15"
            photographer_ids: Optional list to check specific photographers
        
        Returns:
            [
                {
                    "photographer_id": "uuid",
                    "available": true,
                    "reason": "Available on this date"
                }
            ]
        """
        db = await self.get_db()
        
        # Get photographer IDs to check
        if photographer_ids is None:
            # Get all active photographers
            photographers_result = db.table("photographers").select("id").eq(
                "is_active", True
            ).execute()
            photographer_ids = [p["id"] for p in photographers_result.data]
        
        # Check availability for each photographer
        results = []
        for photographer_id in photographer_ids:
            availability = await self.check_availability(photographer_id, date_str)
            results.append({
                "photographer_id": photographer_id,
                **availability
            })
        
        # Return only available photographers
        return [r for r in results if r["available"]]


# Global service instance
_availability_service: Optional[AvailabilityService] = None

def get_availability_service() -> AvailabilityService:
    """Get or create the global availability service instance"""
    global _availability_service
    if _availability_service is None:
        _availability_service = AvailabilityService()
    return _availability_service

# Backward compatibility
def get_booking_service() -> AvailabilityService:
    """Backward compatibility - returns availability service"""
    return get_availability_service()