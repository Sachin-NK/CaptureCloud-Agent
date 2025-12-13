from typing import Dict, Any, List, Optional
import httpx
from app.services.availability_service import get_availability_service
from app.database import get_supabase_agent


class BookingWorkflowService:
   
    
    def __init__(self):
        self.availability_service = get_availability_service()
        self.backend_url = "http://localhost:8080"
        self.mcp_server_url = "http://localhost:8081"
    
    async def process_booking_request(
        self,
        client_id: str,
        photographer_id: str,
        package_id: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Complete booking workflow with availability checking
        
        Args:
            client_id: Client making the request
            photographer_id: Target photographer
            package_id: Selected package
            requirements: Booking requirements (date, location, etc.)
        
        Returns:
            Booking result with status and details
        """
        
        try:
            # Step 1: Validate photographer and package
            photographer_info = await self._get_photographer_info(photographer_id, package_id)
            if not photographer_info["success"]:
                return photographer_info
            
            # Step 2: Check availability (simple date check)
            availability_result = await self._check_availability(
                photographer_id,
                requirements.get("shoot_date", "2024-12-15")
            )
            
            if not availability_result["available"]:
                return {
                    "success": False,
                    "type": "not_available",
                    "message": f"{photographer_info['photographer']['name']} is not available for your requested date.",
                    "reason": availability_result.get("reason", ""),
                    "suggested_action": "choose_different_date_or_photographer"
                }
            
            # Step 3: Create booking in Java backend
            backend_result = await self._create_backend_booking(
                client_id,
                photographer_id,
                package_id,
                requirements
            )
            
            if not backend_result["success"]:
                return backend_result
            
            # Step 4: Booking request sent - Java backend handles the rest
            
            # Step 5: Return success response
            return {
                "success": True,
                "type": "booking_created",
                "message": f"Booking request sent to {photographer_info['photographer']['name']}!",
                "booking_details": {
                    "booking_id": backend_result["booking_id"],
                    "photographer_name": photographer_info["photographer"]["name"],
                    "package_name": photographer_info["package"]["name"],
                    "price": photographer_info["package"]["price"],
                    "status": "pending_photographer_approval",
                    "shoot_date": requirements.get("shoot_date")
                },
                "next_steps": "The photographer will be notified and will respond within 24 hours."
            }
            
        except Exception as e:
            return {
                "success": False,
                "type": "workflow_error",
                "message": "An error occurred while processing your booking request.",
                "error": str(e)
            }
    
    async def _get_photographer_info(self, photographer_id: str, package_id: str) -> Dict[str, Any]:
        """Get photographer and package information"""
        
        try:
            db = await get_supabase_agent()
            
            # Get photographer with package
            response = db.table("photographers").select("""
                id, portfolio_style, location, rating, is_active,
                users!inner (first_name, last_name, email),
                packages!inner (id, name, price, duration_hours, description, is_active)
            """).eq("id", photographer_id).eq("packages.id", package_id).eq("is_active", True).execute()
            
            if not response.data:
                return {
                    "success": False,
                    "type": "photographer_not_found",
                    "message": "Photographer or package not found."
                }
            
            photographer_data = response.data[0]
            user = photographer_data["users"]
            package = photographer_data["packages"][0]
            
            return {
                "success": True,
                "photographer": {
                    "id": photographer_data["id"],
                    "name": f"{user['first_name']} {user['last_name']}".strip(),
                    "email": user["email"],
                    "location": photographer_data["location"],
                    "rating": photographer_data["rating"]
                },
                "package": {
                    "id": package["id"],
                    "name": package["name"],
                    "price": package["price"],
                    "duration_hours": package["duration_hours"],
                    "description": package["description"]
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "type": "database_error",
                "message": "Could not retrieve photographer information."
            }
    
    async def _check_availability(self, photographer_id: str, date: str) -> Dict[str, Any]:
        """Check photographer availability through availability service"""
        
        try:
            result = await self.availability_service.check_availability(
                photographer_id=photographer_id,
                date_str=date
            )
            return result
            
        except Exception as e:
            return {
                "available": False,
                "reason": f"Error checking availability: {str(e)}"
            }
    
    async def _create_backend_booking(
        self,
        client_id: str,
        photographer_id: str,
        package_id: str,
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create booking in Java backend"""
        
        try:
            booking_request = {
                "client_id": client_id,
                "photographer_id": photographer_id,
                "package_id": package_id,
                "requirements": requirements,
                "status": "pending_photographer_approval",
                "availability_confirmed": True
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.backend_url}/api/bookings/create",
                    json=booking_request,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    booking_result = response.json()
                    return {
                        "success": True,
                        "booking_id": booking_result.get("id"),
                        "status": booking_result.get("status")
                    }
                else:
                    return {
                        "success": False,
                        "type": "backend_error",
                        "message": "Could not create booking in backend system."
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "type": "connection_error",
                "message": "Could not connect to booking backend."
            }



# Global service instance
_booking_workflow_service: Optional[BookingWorkflowService] = None

def get_booking_workflow_service() -> BookingWorkflowService:
    """Get or create the global booking workflow service instance"""
    global _booking_workflow_service
    if _booking_workflow_service is None:
        _booking_workflow_service = BookingWorkflowService()
    return _booking_workflow_service