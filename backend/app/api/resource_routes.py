import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from app import research_tasks
from app.utils.url_processor import _summarize_url, sync_summarize_url

router = APIRouter()

@router.get("/research/{task_id}/web-resources")
async def get_web_resources(task_id: str):
    """Fetch web URLs related to the subtopics of a research task."""
    if task_id not in research_tasks:
        raise HTTPException(status_code=404, detail=f"Research task {task_id} not found")
    
    task = research_tasks[task_id]
    
    # Get the subtopics and summary from the task
    subtopics = []
    summary = ""
    main_query = task["query"]
    
    if task.get("immediate_results"):
        if "subtopics" in task["immediate_results"]:
            subtopics = task["immediate_results"]["subtopics"]
        if "summary" in task["immediate_results"]:
            summary = task["immediate_results"]["summary"]
            
        # Check if we already have web resources in immediate_results
        if "web_resources" in task["immediate_results"]:
            web_resources = task["immediate_results"]["web_resources"]
            alternative_resources = task["immediate_results"].get("alternative_perspectives", [])
            
            if web_resources and len(web_resources) > 0:
                # Modified filtering approach to ensure we get 6-7 resources
                filtered_resources = []
                seen_domains = set()
                domain_counts = {}
                
                # Helper function to extract domain from URL
                def get_domain(url):
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc.replace('www.', '')
                        # Get base domain without subdomains
                        parts = domain.split('.')
                        if len(parts) > 2:
                            domain = '.'.join(parts[-2:])
                        return domain
                    except:
                        return url
                
                # First pass - include up to 2 resources from each domain to ensure diversity but get enough results
                for resource in web_resources:
                    domain = get_domain(resource['url'])
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
                    
                    # Allow up to 2 resources per domain
                    if domain_counts[domain] <= 2:
                        filtered_resources.append(resource)
                        
                    # Stop if we have enough resources
                    if len(filtered_resources) >= 7:
                        break
                
                # If we don't have at least 6 resources, add more
                if len(filtered_resources) < 6:
                    for resource in web_resources:
                        if resource not in filtered_resources:
                            filtered_resources.append(resource)
                        if len(filtered_resources) >= 7:
                            break
                
                print(f"Filtered resources: found {len(filtered_resources)} resources from {len(domain_counts)} domains")
                            
                resources_by_type = {
                    "Main Resources": filtered_resources[:7],  # Limit to 7 resources
                }
                
                # Add url_summaries if they exist
                url_summaries = task["immediate_results"].get("url_summaries", {})
                
                # Return these immediately instead of waiting
                print(f"Returning filtered resources for task {task_id} ({len(filtered_resources)} unique domains)")
                return {
                    "task_id": task_id,
                    "query": main_query,
                    "resources_by_subtopic": resources_by_type,
                    "url_summaries": url_summaries,  # Include summaries directly
                    "total_results": len(filtered_resources),
                    "status": "success",
                    "message": "Research results ready"
                }
    
    if task.get("result"):
        if "subtopics" in task["result"]:
            subtopics = task["result"]["subtopics"]
        if "summary" in task["result"]:
            summary = task["result"]["summary"]
    
    if not subtopics:
        raise HTTPException(status_code=400, detail="No subtopics found for this research task")
    
    # Use a timeout mechanism to prevent endless loading
    MAX_TIME = 25  # Maximum seconds to wait for results
    web_results_cache_key = f"{task_id}_web_resources"
    
    # Check if we already have cached results for this task
    try:
        from app import app
        if hasattr(app, 'web_results_cache') and web_results_cache_key in app.web_results_cache:
            cached_result = app.web_results_cache[web_results_cache_key]
            print(f"Returning cached web resources for task {task_id}")
            return cached_result
        
        # Initialize the cache if it doesn't exist
        if not hasattr(app, 'web_results_cache'):
            app.web_results_cache = {}
    except ImportError:
        # Handle the case where app is not available
        print("App module not available for caching")
    
    web_resources_by_subtopic = {}
    all_results = []
    url_summaries = {}  # Store URL summaries
    start_time = time.time()
    
    try:
        # Import WebSearchAgent here to avoid circular imports
        try:
            from app.agents.web_search_agent import WebSearchAgent
            WebSearchAgent_available = True
        except ImportError:
            WebSearchAgent_available = False
            
        if WebSearchAgent_available:
            # Initialize web search agent
            web_agent = WebSearchAgent()
            
            # Start with general resources since they typically work better
            try:
                print(f"Searching for main query: {main_query}")
                # Get more results initially to ensure diversity
                general_results = web_agent.search_web(main_query, num_results=12)
                
                if general_results:
                    # Filter to ensure each result comes from a different domain
                    unique_domain_results = []
                    seen_domains = set()
                    
                    # Helper function to extract domain from URL
                    def get_domain(url):
                        try:
                            from urllib.parse import urlparse
                            return urlparse(url).netloc.replace('www.', '')
                        except:
                            return url
                    
                    # Content relevance check for better filtering
                    def is_relevant(resource, query):
                        # Check if title or snippet contains main query terms
                        query_terms = set(query.lower().split())
                        title_text = resource.get('title', '').lower()
                        snippet_text = resource.get('snippet', '').lower()
                        
                        # Count how many query terms appear
                        title_matches = sum(1 for term in query_terms if term in title_text)
                        snippet_matches = sum(1 for term in query_terms if term in snippet_text)
                        
                        # If resource has good coverage of query terms, consider it relevant
                        return (title_matches >= 1 and snippet_matches >= 1) or snippet_matches >= 2
                    
                    # First prioritize resources that actually contain the query terms
                    for resource in general_results:
                        domain = get_domain(resource['url'])
                        if domain not in seen_domains and is_relevant(resource, main_query):
                            seen_domains.add(domain)
                            unique_domain_results.append(resource)
                            # Get 6-7 diverse and relevant resources
                            if len(unique_domain_results) >= 7:
                                break
                    
                    # If we don't have enough resources, add remaining ones with unique domains
                    if len(unique_domain_results) < 6:
                        for resource in general_results:
                            domain = get_domain(resource['url'])
                            if domain not in seen_domains:
                                seen_domains.add(domain)
                                unique_domain_results.append(resource)
                                if len(unique_domain_results) >= 7:
                                    break
                    
                    web_resources_by_subtopic["Main Resources"] = unique_domain_results[:7]  # Ensure we take up to 7
                    all_results.extend([{**r, 'subtopic': "Main Resources"} for r in unique_domain_results[:7]])
                    print(f"Found {len(unique_domain_results[:7])} resources for the main query")

                    # Automatically generate summaries for the top 3 results
                    for result in unique_domain_results[:3]:
                        try:
                            url_summary = await _summarize_url(result['url'])
                            if url_summary.get("success"):
                                url_summaries[result['url']] = {
                                    "title": result['title'],
                                    "summary": url_summary.get("summary", "No summary available")
                                }
                        except Exception as summary_err:
                            print(f"Error summarizing URL {result['url']}: {str(summary_err)}")
            except Exception as general_error:
                print(f"Error getting general resources: {str(general_error)}")
            
            # Now get specific resources for each subtopic
            for i, subtopic in enumerate(subtopics):
                try:
                    # Check if we're exceeding our time limit
                    if time.time() - start_time > MAX_TIME:
                        print(f"Time limit exceeded after processing {i} subtopics")
                        break
                    
                    print(f"Searching for subtopic {i+1}/{len(subtopics)}: {subtopic}")
                    
                    # Try a regular search first, as it's more reliable
                    search_query = f"{main_query} {subtopic}"
                    results = web_agent.search_web(search_query, num_results=2)
                    
                    # If the regular search fails, try the specialized method
                    if not results:
                        results = web_agent.search_by_subtopic(subtopic, main_query, num_results=2)
                    
                    if results:
                        # Store the results
                        web_resources_by_subtopic[subtopic] = results
                        all_results.extend([{**r, 'subtopic': subtopic} for r in results])
                        print(f"Found {len(results)} resources for: {subtopic}")
                        
                        # Automatically generate a summary for the top result for each subtopic
                        if results and len(results) > 0:
                            try:
                                top_result = results[0]
                                url_summary = await _summarize_url(top_result['url'])
                                if url_summary.get("success"):
                                    url_summaries[top_result['url']] = {
                                        "title": top_result['title'],
                                        "summary": url_summary.get("summary", "No summary available")
                                    }
                            except Exception as summary_err:
                                print(f"Error summarizing URL for subtopic {subtopic}: {str(summary_err)}")
                    else:
                        web_resources_by_subtopic[subtopic] = []
                        print(f"No resources found for: {subtopic}")
                    
                    # Use a small delay to avoid rate limiting
                    time.sleep(0.5)
                    
                except Exception as subtopic_error:
                    print(f"Error with subtopic '{subtopic}': {str(subtopic_error)}")
                    web_resources_by_subtopic[subtopic] = []
                
                # Process at most 3 subtopics to ensure the endpoint returns quickly
                if i >= 2:
                    print(f"Processed the first 3 subtopics, stopping to avoid long loading")
                    break
            
            # If we don't have enough results, use pre-defined reliable URLs
            if len(all_results) < 3:
                print("Not enough results found, adding reliable resources")
                reliable_urls = [
                    {
                        'title': f"{main_query} - Wikipedia",
                        'url': f"https://en.wikipedia.org/wiki/{main_query.replace(' ', '_')}",
                        'snippet': f"Encyclopedia article about {main_query} with comprehensive information."
                    },
                    {
                        'title': f"{main_query} - Academic Research",
                        'url': f"https://scholar.google.com/scholar?q={main_query.replace(' ', '+')}",
                        'snippet': f"Academic papers and research about {main_query}."
                    },
                    {
                        'title': f"{main_query} Latest News",
                        'url': f"https://news.google.com/search?q={main_query.replace(' ', '+')}",
                        'snippet': f"Recent news and developments about {main_query}."
                    }
                ]
                
                web_resources_by_subtopic["Reliable Resources"] = reliable_urls
                all_results.extend([{**r, 'subtopic': "Reliable Resources"} for r in reliable_urls])
                
                # Try to get a summary for Wikipedia
                try:
                    wiki_url = reliable_urls[0]['url']
                    url_summary = await _summarize_url(wiki_url)
                    if url_summary.get("success"):
                        url_summaries[wiki_url] = {
                            "title": reliable_urls[0]['title'],
                            "summary": url_summary.get("summary", "No summary available")
                        }
                except Exception as wiki_err:
                    print(f"Error summarizing Wikipedia URL: {str(wiki_err)}")
            
            # Create the final response with flattened resources list limited to at least 6 items
            response = {
                "task_id": task_id,
                "query": main_query,
                "resources": all_results[:max(7, len(all_results))],  # Get at least 7 or all if less than 7
                "resources_by_subtopic": web_resources_by_subtopic,
                "url_summaries": url_summaries,  
                "total_results": len(all_results[:max(7, len(all_results))]),
                "summarized_urls": len(url_summaries),
                "status": "success",
                "processing_time": f"{time.time() - start_time:.2f} seconds"
            }
            
            # Cache the results if possible
            try:
                from app import app
                if hasattr(app, 'web_results_cache'):
                    app.web_results_cache[web_results_cache_key] = response
            except ImportError:
                pass
            
            return response
                
        else:
            # If WebSearchAgent isn't available, return a meaningful error
            message = "WebSearchAgent not available. Please check your installation."
            print(message)
            return {
                "task_id": task_id,
                "status": "error",
                "message": message,
                "resources_by_subtopic": {}
            }
            
    except Exception as e:
        error_message = f"Error fetching web resources: {str(e)}"
        print(error_message)
        # Return a proper error response
        return {
            "task_id": task_id,
            "status": "error",
            "message": error_message,
            "error": str(e),
            "resources_by_subtopic": {}
        }

@router.post("/summarize-url")
def summarize_url_post(url_data: dict):
    """Fetch and summarize content from a URL using POST."""
    url = url_data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    return sync_summarize_url(url)

@router.get("/summarize-url")
def summarize_url_get(url: str):
    """Fetch and summarize content from a URL using GET."""
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")
    
    return sync_summarize_url(url)