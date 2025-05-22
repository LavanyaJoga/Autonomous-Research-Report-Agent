"""
Enhanced CORS middleware to ensure all origins and OPTIONS requests are properly handled.
This helps solve 404 errors when the frontend makes requests to the backend.
"""

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class EnhancedCORSMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware that handles OPTIONS requests correctly
    and ensures all necessary headers are set.
    """
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Handle OPTIONS requests separately to ensure proper CORS handling
        if request.method == "OPTIONS":
            return Response(
                content="",
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Origin, Accept",
                    "Access-Control-Max-Age": "86400",  # Cache preflight requests for 24 hours
                },
            )
        
        # For other methods, process the request normally
        response = await call_next(request)
        
        # Ensure CORS headers are added to all responses
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, Origin, Accept"
        
        return response
