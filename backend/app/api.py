from fastapi import FastAPI, APIRouter
from .main import app as main_app

# Export the FastAPI app for use by uvicorn
app = main_app
