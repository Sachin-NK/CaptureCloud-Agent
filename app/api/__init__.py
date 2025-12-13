# Package metadata
__version__ = "1.0.0"
__description__ = "REST API endpoints for AI agent service"

# Import the main router
from .routes import router

# Export for easy importing
__all__ = ["router"]
