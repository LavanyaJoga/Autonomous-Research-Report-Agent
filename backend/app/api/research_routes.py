import time
import re
from datetime import datetime
from typing import Dict, Any, List
from fastapi import BackgroundTasks, HTTPException
from app.models.research_models import ResearchRequest
from app import research_tasks
from app.core.task_manager import run_research_task, test_task

# Import web search agent if available
try:
    from app.agents.web_search_agent import WebSearchAgent
    WebSearchAgent_available = True
except ImportError:
    WebSearchAgent_available = False

async def _start_research_common(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Common implementation for starting research tasks."""
    # Generate unique task ID with timestamp and request hash
    unique_id = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{abs(hash(request.query + str(time.time()))) % 10000}"
    task_id = f"task_{unique_id}"
    
    # Debug logging
    print(f"Starting new research task with ID: {task_id}")
    print(f"Query: {request.query}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Initialize immediate_results dict - do this first to avoid undefined variable errors
    immediate_results = {
        "web_resources": [],
        "alternative_perspectives": [],
        "subtopics": [],
        "summary": f"Analyzing '{request.query}'...",
        "url_summaries": {}  # Add a field for URL content summaries
    }
    
    # Generate initial web resources first before any other processing
    web_resources = []
    # Also collect alternative perspectives to provide a balanced view
    alternative_perspectives = []
    
    if WebSearchAgent_available:
        try:
            print(f"Getting initial web resources for: {request.query}")
            web_agent = WebSearchAgent()
            
            # Extract key terms for better search
            try:
                from app.routes.search_routes import extract_key_terms
                query_terms = extract_key_terms(request.query)
                print(f"Extracted key search terms: {query_terms}")
            except Exception as term_error:
                print(f"Error extracting key terms: {str(term_error)}")
                # Simple fallback extraction
                query_terms = [word for word in request.query.split() if len(word) > 3][:5]
            
            # First, do a targeted search with the most important terms
            if query_terms:
                targeted_query = " ".join(query_terms[:3])  # Use top 3 terms
                direct_results = web_agent.search_web(targeted_query, num_results=5)
                if direct_results and len(direct_results) > 0:
                    print(f"Found {len(direct_results)} results with targeted terms: {targeted_query}")
                    # Add a source for tracking
                    for result in direct_results:
                        result['search_method'] = 'targeted_terms'
                    web_resources.extend(direct_results)
            
            # Get direct search results with the full query as a backup
            if len(web_resources) < 5:
                direct_results = web_agent.search_web(request.query, num_results=5)
                if direct_results and len(direct_results) > 0:
                    # Add source information
                    for result in direct_results:
                        if result not in web_resources:
                            result['search_method'] = 'full_query'
                            web_resources.append(result)
                    print(f"Found {len(direct_results)} direct web resources")
            
            # Add initial web resources to immediate_results
            immediate_results["web_resources"] = web_resources
            
            # Add summaries to immediate_results
            url_summaries = _fetch_initial_summaries(web_resources[:3])
            immediate_results["url_summaries"] = url_summaries
            print(f"Added {len(url_summaries)} URL summaries to immediate results")
            
            # Try to extract content from high-relevance resources for better analysis
            analyzed_resources = []
            for resource in web_resources[:3]:  # Analyze top 3 resources
                try:
                    from app.routes.search_routes import extract_and_analyze_content, categorize_domain
                    
                    analysis = extract_and_analyze_content(resource['url'], query_terms)
                    if analysis:
                        domain_category = categorize_domain(resource['url'])
                        analyzed_resources.append({
                            'url': resource['url'],
                            'title': resource['title'],
                            'content_summary': analysis['summary'],
                            'domain_category': domain_category,
                            'relevance_score': analysis['relevance_score']
                        })
                except Exception as content_error:
                    print(f"Error analyzing content: {str(content_error)}")
            
            # Add analyzed resources to the immediate results
            immediate_results["analyzed_resources"] = analyzed_resources
            
            # Try to get alternative perspectives by adding different viewpoint terms to the query
            alternative_queries = [
                f"{request.query} alternative perspective",
                f"{request.query} opposing views",
                f"{request.query} criticism",
                f"{request.query} different approach"
            ]
            
            # Now add specific research-focused queries to get academic and scientific sources
            research_queries = [
                f"{request.query} research paper",
                f"{request.query} scientific study",
                f"{request.query} academic analysis",
                f"{request.query} journal publication"
            ]
            
            # Get academic sources for more in-depth research
            academic_sources = []
            for research_query in research_queries[:2]:  # Limit to 2 to avoid delays
                try:
                    academic_results = web_agent.search_web(research_query, num_results=2)
                    if academic_results:
                        # Add source information
                        for result in academic_results:
                            result['source_type'] = 'academic'
                            result['query_type'] = research_query
                        academic_sources.extend(academic_results)
                except Exception as acad_error:
                    print(f"Error getting academic sources: {str(acad_error)}")
            
            # Add academic sources to the immediate results
            immediate_results["academic_sources"] = academic_sources
            
        except Exception as web_error:
            print(f"Error getting initial web resources: {str(web_error)}")
    
    # Generate immediate results (summary and subtopics) using OpenAI
    try:
        from openai import OpenAI
        client = OpenAI()
        
        print("Generating summary and subtopics with OpenAI...")
        
        # Generate summary with a timeout
        try:
            summary_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a research assistant providing concise, factual summaries."},
                    {"role": "user", "content": f"Provide a 2-3 sentence factual summary about '{request.query}'. Start with 'Summary: '"}
                ],
                temperature=0.2,
                max_tokens=200
            )
            topic_summary = summary_response.choices[0].message.content.strip()
            print("Summary generated successfully")
            immediate_results["summary"] = topic_summary
            
            # Also generate an alternative perspective on the topic
            try:
                alternative_view = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a research assistant that provides alternative perspectives on topics."},
                        {"role": "user", "content": f"Provide a brief alternative perspective or counterpoint on '{request.query}' that differs from the mainstream view. Be factual and balanced. Start with 'Alternative perspective: '"}
                    ],
                    temperature=0.7,  # Higher temperature for more diverse responses
                    max_tokens=150
                )
                alternative_summary = alternative_view.choices[0].message.content.strip()
                print("Alternative perspective generated successfully")
                immediate_results["alternative_view"] = alternative_summary
            except Exception as alt_view_error:
                print(f"Error generating alternative view: {str(alt_view_error)}")
                
        except Exception as summary_error:
            print(f"Error generating summary: {str(summary_error)}")
            immediate_results["summary"] = f"Summary: {request.query} is a topic that requires comprehensive research and analysis."
        
        # Generate subtopics with a timeout
        try:
            subtopics_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a research assistant creating an outline for a research report."},
                    {"role": "user", "content": f"Generate 4-6 specific section headings for a research report on '{request.query}'. Each heading should specifically mention aspects of '{request.query}'. Return only the headings as a numbered list."}
                ],
                temperature=0.5,
                max_tokens=300
            )
            
            # Extract subtopics
            subtopics_text = subtopics_response.choices[0].message.content.strip()
            subtopics = []
            for line in subtopics_text.split('\n'):
                if line.strip():
                    # Clean up the line by removing numbers and periods at the beginning
                    clean_line = re.sub(r'^\d+\.?\s*', '', line.strip())
                    if clean_line:
                        subtopics.append(clean_line)
            
            print(f"Generated {len(subtopics)} subtopics successfully")
            immediate_results["subtopics"] = subtopics
        except Exception as subtopic_error:
            print(f"Error generating subtopics: {str(subtopic_error)}")
            # Fallback to generic subtopics
            immediate_results["subtopics"] = [
                f"Introduction to {request.query}",
                f"Key Concepts of {request.query}",
                f"Applications of {request.query}",
                f"Future Developments in {request.query}"
            ]
        
        print(f"Immediate results generated for task: {task_id}")
        
    except Exception as e:
        print(f"ERROR generating immediate results: {str(e)}")
        immediate_results = {
            "summary": f"Summary: {request.query} is a topic that requires comprehensive research and analysis.",
            "subtopics": [
                f"Introduction to {request.query}",
                f"Key Concepts of {request.query}",
                f"Applications of {request.query}",
                f"Future Developments in {request.query}"
            ],
            "web_resources": web_resources  # Keep the web resources we already got
        }
    
    # Initialize task in storage with the immediate results
    research_tasks[task_id] = {
        "status": "pending",
        "query": request.query,
        "immediate_results": immediate_results,
        "result": None,
        "start_time": datetime.now().isoformat(),
        "progress": 0,
        "current_step": 0,
        "message": "Task initialized",
        "status_details": "Task queued and waiting to start"
    }
    
    # Start full research in background
    try:
        print(f"Adding background task for task_id: {task_id}")
        background_tasks.add_task(run_research_task, task_id, request.query)
        print(f"Background task added successfully for task_id: {task_id}")
    except Exception as e:
        error_message = f"Error adding background task: {str(e)}"
        print(error_message)
        research_tasks[task_id]["status"] = "error"
        research_tasks[task_id]["error"] = error_message
    
    # Return task ID and immediate results with web resources already included
    return {
        "task_id": task_id,
        "status": "pending",
        "message": f"Research task started for query: {request.query}",
        "immediate_results": immediate_results
    }

def _fetch_initial_summaries(resources: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fetch summaries for a batch of web resources."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from app.utils.url_processor import sync_summarize_url
    
    url_summaries = {}
    
    # Define a function to fetch and summarize a single URL
    def fetch_and_summarize_url(url_info):
        try:
            url = url_info["url"]
            title = url_info["title"]
            print(f"Fetching content from {url}")
            
            # Use the synchronous summarization function
            result = sync_summarize_url(url)
            
            if result["success"]:
                return {
                    "url": url,
                    "title": title,
                    "summary": result["summary"],
                    "success": True
                }
            else:
                return {
                    "url": url,
                    "title": title,
                    "summary": f"Could not summarize: {result['error']}",
                    "success": False
                }
        except Exception as e:
            print(f"Error processing URL {url_info.get('url')}: {str(e)}")
            return {
                "url": url_info.get("url", "unknown"),
                "title": url_info.get("title", "Unknown Title"),
                "summary": "Error fetching or processing content.",
                "success": False
            }
    
    # Process URLs with a ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as executor:
        summary_results = list(executor.map(fetch_and_summarize_url, resources))
        
        # Add successful summaries to the result
        for result in summary_results:
            if result["success"]:
                url_summaries[result["url"]] = {
                    "title": result["title"],
                    "summary": result["summary"]
                }
    
    return url_summaries

async def get_research_result(task_id: str):
    """Get the result of a research task."""
    if task_id not in research_tasks:
        raise HTTPException(status_code=404, detail=f"Research task {task_id} not found")
    
    try:
        task = research_tasks[task_id]
        
        # Add detailed logging for debugging
        print(f"Fetching task {task_id} with status: {task.get('status')}")
        
        # Ensure status field exists and has a valid value
        if 'status' not in task or not task['status']:
            print(f"ERROR: Task {task_id} has no valid status field. Setting to error.")
            task['status'] = 'error'
            task['error'] = 'Task has undefined status'
            
        # Get task status with fallback to error if it's invalid
        status = task.get('status')
        if status not in ['pending', 'completed', 'error']:
            print(f"ERROR: Task {task_id} has invalid status: '{status}'. Setting to error.")
            task['status'] = 'error'
            task['error'] = f'Invalid status value: {status}'
            status = 'error'
            
        if status == "pending":
            response = {
                "task_id": task_id,
                "status": "pending",
                "message": "Research in progress"
            }
            
            # Add additional fields if they exist
            for field in ["progress", "current_step", "status_details"]:
                if field in task:
                    response[field] = task[field]
                    
            print(f"Returning pending task info: progress={task.get('progress', 0)}, step={task.get('current_step', 0)}")
            return response
            
        elif status == "completed":
            # Ensure the result has all required fields
            result = task.get("result")
            if not result:
                print(f"ERROR: Task {task_id} marked as completed but has no result")
                return {
                    "task_id": task_id,
                    "status": "error",
                    "message": "Task marked as completed but has no result data"
                }
                
            if not isinstance(result, dict):
                print(f"ERROR: Invalid result format: {type(result)}")
                return {
                    "task_id": task_id,
                    "status": "error",
                    "message": f"Invalid result format: {type(result)}"
                }
                
            # Check for required fields
            required_fields = ["query", "md_path", "pdf_path", "summary", "stats", "subtopics"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                print(f"ERROR: Research result missing fields: {missing_fields}")
                print(f"Available fields: {list(result.keys())}")
                
                # Instead of failing, try to provide a meaningful result with defaults
                for field in missing_fields:
                    if field == "query" and "query" in task:
                        result["query"] = task["query"]
                    elif field == "md_path":
                        result["md_path"] = f"reports/{task_id}_report.md"
                    elif field == "pdf_path":
                        result["pdf_path"] = f"reports/{task_id}_report.pdf"
                    elif field == "summary" and task.get("immediate_results", {}).get("summary"):
                        result["summary"] = task["immediate_results"]["summary"]
                    elif field == "stats":
                        result["stats"] = "Sources: Generated with available resources"
                    elif field == "subtopics" and task.get("immediate_results", {}).get("subtopics"):
                        result["subtopics"] = task["immediate_results"]["subtopics"]
                    else:
                        # Default fallback values
                        if field == "summary":
                            result[field] = f"Research on {result.get('query', 'the topic')} completed successfully."
                        elif field == "subtopics":
                            result[field] = ["Introduction", "Key Concepts", "Applications", "Conclusion"]
                        else:
                            result[field] = f"Generated {field}"
                            
                print(f"Filled in missing fields with defaults: {missing_fields}")
                
            result["status"] = "completed"  # Ensure status is in the result
            result["task_id"] = task_id     # Include task_id for reference
            
            print(f"Returning completed result for {task_id}")
            return result
            
        else:  # error
            error_details = {
                "task_id": task_id,
                "status": "error",
                "message": f"Research task failed: {task.get('error', 'Unknown error')}",
            }
            
            # Add traceback if available
            if "traceback" in task:
                error_details["traceback"] = task["traceback"]
                
            # Add status details if available
            if "status_details" in task:
                error_details["status_details"] = task["status_details"]
            
            print(f"Returning error for task {task_id}: {error_details['message']}")
            return error_details  # Return instead of raising exception
            
    except Exception as e:
        print(f"ERROR in get_research_result: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {
            "task_id": task_id,
            "status": "error",
            "message": f"Server error retrieving task: {str(e)}"
        }

async def get_task_status(task_id: str):
    """Get detailed status of a task."""
    if task_id not in research_tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = research_tasks[task_id]
    
    # Return all task details except the actual result data to keep the response small
    status_info = {k: v for k, v in task.items() if k != "result"}
    
    # Add result summary if completed
    if task["status"] == "completed" and task.get("result"):
        status_info["summary"] = task["result"].get("summary", "No summary available")
    
    return status_info

async def start_test_task(background_tasks: BackgroundTasks):
    """Start a test task to verify background processing."""
    task_id = f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Initialize task
    research_tasks[task_id] = {
        "status": "pending",
        "query": "Test query",
        "result": None,
        "start_time": datetime.now().isoformat(),
        "progress": 0,
        "current_step": 0,
        "message": "Test task initialized",
        "status_details": "Test task queued"
    }
    
    # Add the test task to the background tasks
    background_tasks.add_task(test_task, task_id)
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Test task started"
    }

async def clear_cache():
    """Clear all caches in the application."""
    try:
        from fastapi import FastAPI
        from app import app
        
        # Clear web results cache
        if hasattr(app, 'web_results_cache'):
            cache_size = len(app.web_results_cache)
            app.web_results_cache.clear()
            print(f"Cleared web results cache ({cache_size} entries)")
        else:
            print("No web results cache to clear")
        
        # Clear research tasks
        if 'research_tasks' in globals():
            task_count = len(research_tasks)
            # Keep completed tasks but clear results to reduce memory
            for task_id in research_tasks:
                if research_tasks[task_id].get("status") == "completed":
                    research_tasks[task_id]["result"] = {"cleared": True}
                    research_tasks[task_id]["immediate_results"] = {"cleared": True}
            print(f"Cleaned up {task_count} research tasks")
        else:
            print("No research tasks to clear")
            
        return {
            "status": "success",
            "message": "All caches cleared successfully"
        }
    except Exception as e:
        print(f"Error clearing cache: {str(e)}")
        return {
            "status": "error",
            "message": f"Error clearing cache: {str(e)}"
        }