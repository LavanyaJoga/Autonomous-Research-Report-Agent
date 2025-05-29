# Create a new file: backend/app/core/app_init.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Create and configure the FastAPI app
def create_app():
    app = FastAPI(
        title="Research-Report-Agent API",
        description="API for autonomous research and report generation",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    return app

def init_app():
    """Initialize the application and create necessary directories."""
    # Create necessary directories
    os.makedirs("./reports", exist_ok=True)
    os.makedirs("./cache", exist_ok=True)
    
    # Return success message
    return {"status": "initialized", "directories": ["./reports", "./cache"]}