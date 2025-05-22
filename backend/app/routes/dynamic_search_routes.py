"""
API routes for dynamic web search functionality that returns truly relevant web sources.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any
import asyncio
import logging
import traceback

from app.services.dynamic_web_search import DynamicWebSearch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/dynamic-search")
async def dynamic_search(
    query: str = Query(..., description="Search query"),
    min_results: int = Query(7, description="Minimum number of results")
):
    """
    Perform dynamic web search across multiple search engines.
    Returns diverse, relevant results from at least 7 different domains.
    """
    try:
        # Initialize dynamic web search
        search_service = DynamicWebSearch()
        
        # Perform search
        results = await search_service.search(query, min_results=min_results)
        
        # Count unique domains
        domains = set()
        for result in results:
            url = result.get("url", "")
            if url:
                domain = search_service._get_domain(url)
                domains.add(domain)
        
        # Return results
        return {
            "query": query,
            "results": results,
            "count": len(results),
            "unique_domains": len(domains),
            "domains": list(domains)
        }
    except Exception as e:
        logger.error(f"Error in dynamic search: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )
