import asyncio
from typing import Dict, Any
import traceback

async def _summarize_url(url: str) -> Dict[str, Any]:
    """Async helper function to summarize URL content."""
    try:
        from app.utils.content_extractor import fetch_url_content, get_page_summary
        
        # Log the request for debugging
        print(f"Summarizing URL: {url}")
        
        # Fetch the content with our robust fetcher
        result = fetch_url_content(url)
        
        if not result["success"]:
            print(f"Failed to fetch content from {url}: {result['error']}")
            return {
                "url": url,
                "success": False,
                "error": result["error"],
                "message": f"Failed to fetch content: {result['error']}"
            }
        
        # Generate summary if we got content
        if result["content"]:
            summary = get_page_summary(url, result["content"])
            print(f"Successfully summarized {url}: {len(summary)} chars")
            return {
                "url": url,
                "title": result["title"],
                "description": result["description"],
                "summary": summary,
                "success": True
            }
        else:
            print(f"No content extracted from {url}")
            return {
                "url": url,
                "success": False,
                "error": "No content extracted",
                "message": "Could not extract meaningful content from the URL"
            }
    except Exception as e:
        print(f"Error summarizing URL {url}: {str(e)}")
        traceback.print_exc()
        return {
            "url": url,
            "success": False,
            "error": str(e),
            "message": f"Server error: {str(e)}"
        }

def sync_summarize_url(url: str) -> Dict[str, Any]:
    """Synchronous version of the URL summarization function."""
    try:
        from app.utils.content_extractor import fetch_url_content, get_page_summary
        
        print(f"Summarizing URL (sync): {url}")
        
        # Fetch the content
        result = fetch_url_content(url)
        
        if not result["success"]:
            return {
                "url": url,
                "success": False,
                "error": result["error"],
                "message": f"Failed to fetch content: {result['error']}"
            }
        
        # Generate summary if we got content
        if result["content"]:
            summary = get_page_summary(url, result["content"])
            return {
                "url": url,
                "title": result["title"],
                "description": result["description"],
                "summary": summary,
                "success": True
            }
        else:
            return {
                "url": url,
                "success": False,
                "error": "No content extracted",
                "message": "Could not extract meaningful content from the URL"
            }
    except Exception as e:
        print(f"Error in sync summarize URL {url}: {str(e)}")
        traceback.print_exc()
        return {
            "url": url,
            "success": False,
            "error": str(e),
            "message": f"Server error: {str(e)}"
        }