"""
Routes for research functionality with true dynamic web sources.
"""

import asyncio
import logging
import traceback
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.services.web_content_retriever import WebContentRetriever
from app.services.web_analyzer import WebAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    min_sources: Optional[int] = Field(7, ge=3, le=15)
    analyze_content: Optional[bool] = True

class ResearchResponse(BaseModel):
    task_id: str
    status: str
    immediate_results: Optional[Dict[str, Any]] = None

@router.post("/research")
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """
    Start a research task with dynamic web sources.
    Returns immediate search results and continues processing in the background.
    """
    try:
        # Generate a task ID
        import uuid
        task_id = str(uuid.uuid4())
        
        # Get immediate search results using our dynamic content retriever
        web_content_retriever = WebContentRetriever()
        web_resources = await web_content_retriever.get_dynamic_web_sources(
            query=request.query,
            min_sources=request.min_sources
        )
        
        logger.info(f"Got {len(web_resources)} immediate web resources for '{request.query}'")
        
        # Create immediate results
        immediate_results = {
            "web_resources": web_resources,
            "query": request.query
        }
        
        # Start background task for deeper analysis if requested
        if request.analyze_content:
            web_analyzer = WebAnalyzer()
            background_tasks.add_task(
                complete_research_task, 
                task_id=task_id,
                query=request.query,
                min_sources=request.min_sources,
                web_analyzer=web_analyzer
            )
            
            status = "processing"
        else:
            status = "completed"
        
        # Return response with task ID and immediate results
        return {
            "task_id": task_id,
            "status": status,
            "immediate_results": immediate_results
        }
        
    except Exception as e:
        logger.error(f"Error starting research: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start research: {str(e)}"
        )

async def complete_research_task(task_id: str, query: str, min_sources: int, web_analyzer: WebAnalyzer):
    """Complete the research task in the background."""
    try:
        # Store this in a task service or database
        from app.services.task_service import TaskService
        
        # Create task if it doesn't exist
        if not TaskService.get_task(task_id):
            TaskService.create_task(
                task_id=task_id,
                topic=query,
                parameters={"min_sources": min_sources}
            )
        
        # Update task status
        TaskService.update_task_status(task_id, "processing", "Analyzing web content")
        
        # Get comprehensive research sources with content analysis
        research_result = await web_analyzer.get_research_sources(
            query=query,
            min_sources=min_sources
        )
        
        # Update task with results
        TaskService.update_task_result(task_id, research_result)
        TaskService.update_task_status(task_id, "completed", "Research complete")
        
        logger.info(f"Completed research task {task_id} for '{query}'")
        
    except Exception as e:
        logger.error(f"Error completing research task {task_id}: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Update task with error
        from app.services.task_service import TaskService
        TaskService.update_task_status(task_id, "error", f"Error: {str(e)}")

@router.get("/research/{task_id}")
async def get_research_status(task_id: str):
    """Get the status and results of a research task."""
    try:
        from app.services.task_service import TaskService
        
        task = TaskService.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Research task {task_id} not found"
            )
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting research status: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get research status: {str(e)}"
        )
