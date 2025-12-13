"""
Permission Utilities
====================
Helper functions to verify user permissions before database operations.
Even though we use agent_client (which has broad access), we still need
to verify that users can only access their own data.

Security Principle: Trust but Verify
- Agent client has technical ability to access any data
- But we verify permissions in application code
- This prevents unauthorized access
"""

from typing import Optional
from app.database import get_supabase_agent

class PermissionError(Exception):
    """Raised when user doesn't have permission for an operation"""
    pass

async def verify_booking_ownership(booking_id: int, user_id: str) -> bool:
    """
    Verify that a booking belongs to a specific user
    
    Args:
        booking_id: The booking ID to check
        user_id: The user ID claiming ownership
        
    Returns:
        bool: True if user owns the booking
        
    Raises:
        PermissionError: If user doesn't own the booking
    """
    db = get_supabase_agent()
    
    result = db.table("bookings").select("user_id").eq("id", booking_id).execute()
    
    if not result.data:
        raise PermissionError(f"Booking {booking_id} not found")
    
    if result.data[0]["user_id"] != user_id:
        raise PermissionError("You can only access your own bookings")
    
    return True

async def verify_restaurant_staff(user_id: str, restaurant_id: int) -> bool:
    """
    Verify that a user is staff at a specific restaurant
    
    Args:
        user_id: The user ID to check
        restaurant_id: The restaurant ID
        
    Returns:
        bool: True if user is staff at this restaurant
        
    Raises:
        PermissionError: If user is not staff
    """
    db = get_supabase_agent()
    
    result = db.table("restaurant_staff").select("*").eq("user_id", user_id).eq("restaurant_id", restaurant_id).execute()
    
    if not result.data:
        raise PermissionError("You are not staff at this restaurant")
    
    return True

async def can_modify_booking(booking_id: int, user_id: str, role: Optional[str] = None) -> bool:
    """
    Check if user can modify a booking
    
    Rules:
    - Users can modify their own bookings
    - Restaurant staff can modify bookings at their restaurant
    - System operations (role='system') can modify any booking
    
    Args:
        booking_id: The booking to modify
        user_id: The user requesting modification
        role: Optional role ('user', 'staff', 'system')
        
    Returns:
        bool: True if modification is allowed
    """
    db = get_supabase_agent()
    
    # Get booking details
    booking = db.table("bookings").select("user_id, restaurant_id").eq("id", booking_id).execute()
    
    if not booking.data:
        raise PermissionError(f"Booking {booking_id} not found")
    
    booking_data = booking.data[0]
    
    # Check ownership
    if booking_data["user_id"] == user_id:
        return True
    
    # Check if restaurant staff
    if role == "staff":
        return await verify_restaurant_staff(user_id, booking_data["restaurant_id"])
    
    # System operations allowed
    if role == "system":
        return True
    
    raise PermissionError("You don't have permission to modify this booking")
