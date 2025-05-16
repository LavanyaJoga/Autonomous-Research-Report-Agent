from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import time
from datetime import datetime
import re
import requests
from urllib.parse import quote_plus
import json
from bs4 import BeautifulSoup

# Import agents
from app.agents.web_search_agent import WebSearchAgent

# Import the new LangChain search agent
try:
    from app.agents.langchain_search_agent import LangChainSearchAgent
    LANGCHAIN_AGENT_AVAILABLE = True
    print("LangChain search agent imported successfully")
except ImportError:
    LANGCHAIN_AGENT_AVAILABLE = False
    print("LangChain search agent not available")

# Create router
router = APIRouter()

# Define request models
class ReportRequest(BaseModel):
    query: str = Field(..., min_length=10, description="The research topic/query")
    subtopics: Optional[List[str]] = Field(None, description="Optional subtopics to include")
    sources: Optional[List[str]] = Field(None, description="Optional specific URLs to include")
    depth: Optional[str] = Field("medium", description="Research depth: 'basic', 'medium', or 'deep'")

class ReportResponse(BaseModel):
    task_id: str = Field(..., description="ID to track the report generation task")
    status: str = Field(..., description="Status of the task")
    message: str = Field(..., description="Status message")

# Store background tasks
report_tasks = {}

@router.post("/generate-report", response_model=ReportResponse)
async def generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    """Generate a comprehensive research report on a topic."""
    task_id = f"report_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(request.query) % 10000}"
    
    # Initialize agents
    web_agent = WebSearchAgent()
    
    # Store task
    report_tasks[task_id] = {
        "status": "pending",
        "query": request.query,
        "start_time": datetime.now().isoformat(),
        "message": "Report generation started",
        "progress": 0
    }
    
    # Start background task
    background_tasks.add_task(
        run_report_generation,
        task_id=task_id,
        query=request.query,
        subtopics=request.subtopics,
        sources=request.sources,
        depth=request.depth
    )
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": f"Report generation started for: {request.query}"
    }

@router.get("/report-status/{task_id}")
async def get_report_status(task_id: str):
    """Check the status of a report generation task."""
    if task_id not in report_tasks:
        raise HTTPException(status_code=404, detail=f"Report task {task_id} not found")
    
    return report_tasks[task_id]

@router.get("/download-report/{task_id}")
async def download_report(task_id: str, format: str = "md"):
    """Download a completed report."""
    if task_id not in report_tasks:
        raise HTTPException(status_code=404, detail=f"Report task {task_id} not found")
    
    task = report_tasks[task_id]
    
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Report not yet completed")
    
    if format == "md":
        file_path = task["result"]["md_path"]
    elif format == "pdf":
        file_path = task["result"]["pdf_path"]
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Report file not found")
    
    # Return file
    from fastapi.responses import FileResponse
    return FileResponse(
        path=file_path, 
        filename=os.path.basename(file_path),
        media_type='application/octet-stream'
    )

# Add new search engines to diversify results
class WebResearchEngine:
    """Implements direct web search capabilities without relying on AI for content."""
    
    def __init__(self):
        # Get User-Agent from environment variables or use default
        self.user_agent = os.environ.get(
            "USER_AGENT", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Log a warning if USER_AGENT is not set
        if "USER_AGENT" not in os.environ:
            print("WARNING: USER_AGENT environment variable not set, using default. Consider setting it to identify your requests.")
        
    def search_duckduckgo(self, query, num_results=5):
        """Direct DuckDuckGo search scraping."""
        try:
            # Encode the query for URL
            encoded_query = quote_plus(query)
            url = f"https://duckduckgo.com/html/?q={encoded_query}"
            
            # Use the user_agent from instance variable
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all result elements
            results = []
            for result in soup.select('.result'):
                # Extract title, URL and snippet
                title_elem = result.select_one('.result__title')
                url_elem = result.select_one('.result__url')
                snippet_elem = result.select_one('.result__snippet')
                
                if title_elem and url_elem:
                    title = title_elem.get_text().strip()
                    url = url_elem.get('href') if url_elem.has_attr('href') else ""
                    snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                    
                    # Clean up URL
                    if url.startswith('/'):
                        url = 'https://duckduckgo.com' + url
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'source': 'duckduckgo'
                    })
                    
                    # Limit to requested number
                    if len(results) >= num_results:
                        break
            
            return results
            
        except Exception as e:
            print(f"DuckDuckGo search error: {str(e)}")
            return []
    
    def search_google(self, query, num_results=5):
        """Search Google directly."""
        try:
            # Attempt to use SerpAPI if key is available
            serp_api_key = os.environ.get("SERPAPI_KEY")
            if serp_api_key:
                return self._search_serpapi(query, num_results)
                
            # Fallback to basic web search
            encoded_query = quote_plus(query)
            url = f"https://www.google.com/search?q={encoded_query}&num={num_results}&hl=en"
            
            # Use the user_agent from instance variable
            headers = {
                'User-Agent': self.user_agent,
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the results
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for g in soup.find_all('div', class_='g'):
                # Extract title and link
                title_elem = g.find('h3')
                if not title_elem:
                    continue
                    
                title = title_elem.get_text()
                
                # Find the URL
                a_tag = g.find('a')
                if not a_tag:
                    continue
                    
                link = a_tag.get('href', '')
                
                # Clean URL
                if link.startswith('/url?q='):
                    link = link[7:]
                    link = link.split('&sa=')[0]
                
                # Find snippet
                snippet_elem = g.find('div', class_='VwiC3b')
                snippet = snippet_elem.get_text() if snippet_elem else ""
                
                results.append({
                    'title': title,
                    'url': link,
                    'snippet': snippet,
                    'source': 'google'
                })
                
                if len(results) >= num_results:
                    break
            
            return results
            
        except Exception as e:
            print(f"Google search error: {str(e)}")
            return []
    
    def _search_serpapi(self, query, num_results=5):
        """Use SerpAPI for Google search."""
        try:
            api_key = os.environ.get("SERPAPI_KEY")
            
            if not api_key:
                return []
                
            encoded_query = quote_plus(query)
            url = f"https://serpapi.com/search.json?q={encoded_query}&num={num_results}&api_key={api_key}"
            
            response = requests.get(url, timeout=10)
            data = response.json()
            
            results = []
            if 'organic_results' in data:
                for item in data['organic_results'][:num_results]:
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'source': 'serpapi'
                    })
            
            return results
            
        except Exception as e:
            print(f"SerpAPI error: {str(e)}")
            return []
    
    def extract_content(self, url):
        """Extract main content from a webpage."""
        try:
            # Get User-Agent from environment variables or use default
            user_agent = os.environ.get(
                "USER_AGENT", 
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            # Log a warning if USER_AGENT is not set
            if "USER_AGENT" not in os.environ:
                print("WARNING: USER_AGENT environment variable not set, using default. Consider setting it to identify your requests.")
            
            headers = {'User-Agent': user_agent}
            
            # Make the request
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Get the content type
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Skip non-HTML content
            if 'text/html' not in content_type:
                return ""
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                tag.decompose()
            
            # Try to find main content
            main_content = None
            
            # Try common content containers
            for selector in ['article', 'main', '.content', '#content', '.post', '.entry-content', '[role="main"]']:
                element = soup.select_one(selector)
                if element:
                    main_content = element
                    break
            
            # If no main content found, use body
            if not main_content:
                main_content = soup.body
            
            # Get paragraphs
            paragraphs = []
            if main_content:
                # Get all paragraphs
                for p in main_content.find_all('p'):
                    text = p.get_text().strip()
                    if len(text) > 40:  # Skip very short paragraphs
                        paragraphs.append(text)
            
            # Join paragraphs
            content = "\n\n".join(paragraphs)
            
            # Clean up
            content = re.sub(r'\s+', ' ', content).strip()
            
            return content
            
        except Exception as e:
            print(f"Error extracting content from {url}: {str(e)}")
            return ""

def run_report_generation(task_id: str, query: str, subtopics: Optional[List[str]], 
                         sources: Optional[List[str]], depth: str):
    """Run the report generation process in the background."""
    try:
        # Update task status
        report_tasks[task_id]["status_details"] = "Initializing research..."
        
        # Initialize the direct web research engine
        research_engine = WebResearchEngine()
        
        # Set up output directory
        output_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Generate or validate subtopics
        report_tasks[task_id]["status_details"] = "Finding topic information..."
        report_tasks[task_id]["progress"] = 0.1
        
        # Search for initial information about the topic
        duckduckgo_results = research_engine.search_duckduckgo(query, num_results=7)
        google_results = research_engine.search_google(query, num_results=7)
        
        # Combine results
        initial_results = duckduckgo_results + google_results
        
        # Deduplicate by URL
        seen_urls = set()
        unique_initial_results = []
        for result in initial_results:
            url = result.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_initial_results.append(result)
        
        # If user provided subtopics, use them
        if subtopics and len(subtopics) >= 3:
            print(f"Using {len(subtopics)} user-provided subtopics")
        else:
            # Generate subtopics based on search results
            subtopics = []
            
            # Extract content from top results to analyze for subtopics
            all_content = ""
            for result in unique_initial_results[:3]:
                url = result.get('url')
                content = research_engine.extract_content(url)
                all_content += " " + content
            
            # Clean the content
            all_content = re.sub(r'[^\w\s]', ' ', all_content)
            all_content = re.sub(r'\s+', ' ', all_content).strip()
            
            # Look for section patterns
            section_patterns = [
                r"(?:^|\s)(?:section|chapter|part)\s+\d+:?\s+([A-Z][^\.]+)",
                r"(?:^|\s)(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.?\s+([A-Z][^\.]+)",
                r"(?:^|\s)(?:\d+)\.(?:\d+)?\s+([A-Z][^\.]+)",
                r"(?:^|\s)(?:[A-Z])\.?\s+([A-Z][^\.]+)",
                r"(?<!\w)(?:Types|Components|Elements|Factors|Aspects|Features|Benefits|Advantages|Parts|Stages|Phases|Steps)\s+of\s+([^\.]+)",
                r"<h\d[^>]*>([^<]+)</h\d>"
            ]
            
            # Extract potential sections
            potential_sections = []
            for pattern in section_patterns:
                matches = re.findall(pattern, all_content, re.IGNORECASE)
                potential_sections.extend(matches)
            
            # Clean up and filter sections
            for section in potential_sections:
                # Clean the section name
                clean_section = section.strip()
                
                # Skip if too short or too long
                if len(clean_section) < 10 or len(clean_section) > 80:
                    continue
                
                # Skip if doesn't contain letters
                if not re.search(r'[a-zA-Z]', clean_section):
                    continue
                
                # Add to subtopics
                if clean_section not in subtopics:
                    subtopics.append(clean_section)
            
            # If we couldn't find good subtopics, create generic ones
            if len(subtopics) < 3:
                # Analyze search results to guess subtopics
                key_terms = set()
                for result in unique_initial_results:
                    title = result.get('title', '').lower()
                    snippet = result.get('snippet', '').lower()
                    
                    # Look for key terms in title and snippet
                    title_terms = re.findall(r'\b\w{5,}\b', title)
                    snippet_terms = re.findall(r'\b\w{5,}\b', snippet)
                    
                    key_terms.update(title_terms)
                    key_terms.update(snippet_terms)
                
                # Filter out common words
                common_words = {'about', 'after', 'again', 'below', 'could', 'every', 'first', 'found', 'great', 'might', 'other', 'their', 'there', 'these', 'thing', 'think', 'those', 'would'}
                key_terms = [term for term in key_terms if term not in common_words]
                
                # Use the key terms to create subtopics
                subtopics = [
                    f"History and Background of {query}",
                    f"Key Components and Elements of {query}",
                    f"Applications and Use Cases for {query}",
                ]
                
                # Add some key-term based subtopics
                if key_terms:
                    for term in list(key_terms)[:2]:
                        subtopics.append(f"The Role of {term.capitalize()} in {query}")
                
                # Add a future-oriented subtopic
                subtopics.append(f"Future Developments and Trends in {query}")
        
        # Store subtopics in task
        report_tasks[task_id]["subtopics"] = subtopics
        
        # Step 2: Find relevant sources
        report_tasks[task_id]["status_details"] = "Finding relevant sources..."
        report_tasks[task_id]["progress"] = 0.2
        
        # Get sources from web search
        search_results = []
        
        # If user provided specific sources, include them
        if sources and len(sources) > 0:
            # Add user-provided sources
            for url in sources:
                search_results.append({
                    'title': f"User provided source: {url}",
                    'url': url,
                    'snippet': "User-provided source for research."
                })
        
        # Get sources for each subtopic
        for i, subtopic in enumerate(subtopics):
            try:
                # Create a combined query for better results
                search_query = f"{query} {subtopic}"
                
                # Determine number of results based on depth
                num_results = 2 if depth == "basic" else 3 if depth == "medium" else 5
                
                # Perform search
                results = web_agent.search_web(search_query, num_results=num_results)
                
                if results:
                    # Add subtopic info to each result
                    for result in results:
                        result['subtopic'] = subtopic
                    
                    # Add to overall results
                    search_results.extend(results)
                    
                    # Update progress
                    progress = 0.2 + (0.3 * (i + 1) / len(subtopics))
                    report_tasks[task_id]["progress"] = progress
                    report_tasks[task_id]["status_details"] = f"Found sources for subtopic: {subtopic}"
            except Exception as search_error:
                print(f"Error searching for subtopic {subtopic}: {str(search_error)}")
        
        # Deduplicate sources
        unique_urls = set()
        unique_results = []
        
        for result in search_results:
            url = result.get('url')
            if url and url not in unique_urls:
                unique_urls.add(url)
                unique_results.append(result)
        
        # Step 3: Extract and process content from sources
        report_tasks[task_id]["status_details"] = "Extracting and analyzing content..."
        report_tasks[task_id]["progress"] = 0.5
        
        # Process the sources - implement direct web scraping without ContentProcessor
        processed_sources = []
        
        for i, source in enumerate(unique_results):
            try:
                url = source.get('url')
                
                # Extract content directly with requests and BeautifulSoup
                import requests
                from bs4 import BeautifulSoup
                
                # Use a browser-like User-Agent
                headers = {
                    "User-Agent": research_engine.user_agent
                }
                
                try:
                    # Get the web page
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    
                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Remove unwanted elements
                    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                        element.decompose()
                    
                    # Try to find the main content
                    main_content = None
                    
                    # Common content container elements
                    content_selectors = [
                        "article", "main", ".content", "#content", ".post", ".entry", 
                        "[role='main']", ".article", ".post-content", ".entry-content"
                    ]
                    
                    # Try each selector
                    for selector in content_selectors:
                        content_element = soup.select_one(selector)
                        if content_element:
                            main_content = content_element
                            break
                    
                    # If we couldn't find a specific content container, use the body
                    if not main_content:
                        main_content = soup.body
                    
                    # Extract text
                    if main_content:
                        # Get paragraphs
                        paragraphs = main_content.find_all('p')
                        content_text = "\n".join([p.get_text().strip() for p in paragraphs])
                        
                        # If no paragraphs found, get all text
                        if not content_text:
                            content_text = main_content.get_text(separator='\n', strip=True)
                        
                        # Clean up content
                        content_text = re.sub(r'\s+', ' ', content_text).strip()
                        
                        # Add content to the source
                        source['content'] = content_text
                        
                        # Simple keyword analysis to determine relevance
                        subtopic_terms = source.get('subtopic', '').lower().split()
                        query_terms = query.lower().split()
                        relevance_terms = subtopic_terms + query_terms
                        
                        # Count occurrences of relevant terms
                        term_count = sum(1 for term in relevance_terms if term.lower() in content_text.lower())
                        
                        # Calculate a simple relevance score (0-10)
                        relevance_score = min(10, term_count)
                        
                        # Extract key sentences containing the query or subtopic terms
                        sentences = re.split(r'(?<=[.!?])\s+', content_text)
                        key_sentences = [
                            sentence for sentence in sentences 
                            if any(term.lower() in sentence.lower() for term in relevance_terms)
                        ]
                        
                        # Take the first few key sentences as "quotes"
                        quotes = key_sentences[:5]
                        
                        # Add analysis to the source
                        source['analysis'] = {
                            'relevance': relevance_score,
                            'key_points': [f"From {source['title']}: {quote[:100]}..." for quote in quotes[:3]],
                            'quotes': quotes
                        }
                        
                        # Add to processed sources if relevant enough
                        if relevance_score > 3:
                            processed_sources.append(source)
                except Exception as request_error:
                    print(f"Error requesting URL {url}: {str(request_error)}")
                
                # Update progress
                progress = 0.5 + (0.2 * (i + 1) / len(unique_results))
                report_tasks[task_id]["progress"] = progress
                report_tasks[task_id]["status_details"] = f"Processed source {i+1}/{len(unique_results)}"
            except Exception as process_error:
                print(f"Error processing source {source.get('url')}: {str(process_error)}")
        
        # Step 4: Generate the report
        report_tasks[task_id]["status_details"] = "Generating final report..."
        report_tasks[task_id]["progress"] = 0.8
        
        # Generate the report directly instead of using ContentProcessor
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s]', '', query.lower()).replace(' ', '_')[:30]
        filename_base = f"{safe_query}_{timestamp}"
        
        # Create output paths
        md_path = os.path.join(output_dir, f"{filename_base}.md")
        pdf_path = os.path.join(output_dir, f"{filename_base}.pdf")
        
        # Start building the report
        report_content = f"# Research Report: {query}\n\n"
        
        # Executive summary
        summary_text = f"This research report presents findings on '{query}', covering various aspects including {', '.join(subtopics[:3])}. The report synthesizes information from {len(processed_sources)} web sources to provide a comprehensive overview of the topic."
        report_content += f"## Executive Summary\n\n{summary_text}\n\n"
        
        # Group sources by subtopic
        sources_by_subtopic = {}
        for subtopic in subtopics:
            sources_by_subtopic[subtopic] = []
        
        # Add sources to their respective subtopics
        for source in processed_sources:
            subtopic = source.get('subtopic')
            if subtopic in sources_by_subtopic:
                sources_by_subtopic[subtopic].append(source)
        
        # Generate content for each subtopic
        for subtopic in subtopics:
            report_content += f"## {subtopic}\n\n"
            
            # Get sources for this subtopic
            subtopic_sources = sources_by_subtopic.get(subtopic, [])
            
            if subtopic_sources:
                # Collect quotes from all sources for this subtopic
                all_quotes = []
                for source in subtopic_sources:
                    analysis = source.get('analysis', {})
                    quotes = analysis.get('quotes', [])
                    if quotes:
                        all_quotes.extend(quotes[:2])  # Use up to 2 quotes per source
                
                # If we have quotes, use them to create content
                if all_quotes:
                    # Add content based on quotes
                    for i, quote in enumerate(all_quotes[:5]):  # Use up to 5 quotes
                        # Clean up the quote
                        clean_quote = quote.strip()
                        
                        # Add the quote with citation number
                        source_index = processed_sources.index(subtopic_sources[min(i, len(subtopic_sources)-1)])
                        report_content += f"{clean_quote} [{source_index + 1}]\n\n"
                else:
                    report_content += f"No specific information was found for this subtopic.\n\n"
            else:
                report_content += f"No specific sources were found for this subtopic.\n\n"
        
        # Add references section
        report_content += "## References\n\n"
        for i, source in enumerate(processed_sources, 1):
            title = source.get('title', 'Untitled Source')
            url = source.get('url', '')
            report_content += f"{i}. [{title}]({url})\n"
        
        # Write to markdown file
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # Try to generate PDF
        try:
            # Try to use markdown2pdf if available
            from weasyprint import HTML
            import markdown
            
            # Convert markdown to HTML
            md_content = report_content
            html_content = markdown.markdown(md_content)
            
            # Add basic styling
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 3cm; line-height: 1.5; }}
                    h1 {{ color: #333366; }}
                    h2 {{ color: #333366; margin-top: 1.5em; }}
                    a {{ color: #0066cc; }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            # Generate PDF
            HTML(string=styled_html).write_pdf(pdf_path)
        except Exception as pdf_error:
            print(f"Error generating PDF: {str(pdf_error)}")
            # Create a dummy PDF path reference
            pdf_path = "PDF generation not available"
        
        # Create report result
        report_result = {
            "md_path": md_path,
            "pdf_path": pdf_path,
            "sections": len(subtopics),
            "sources": len(processed_sources)
        }
        
        # Update task with result
        report_tasks[task_id]["status"] = "completed"
        report_tasks[task_id]["result"] = report_result
        report_tasks[task_id]["completion_time"] = datetime.now().isoformat()
        report_tasks[task_id]["progress"] = 1.0
        report_tasks[task_id]["status_details"] = "Report generation completed successfully"
        
    except Exception as e:
        import traceback
        error_message = f"Error in report generation: {str(e)}"
        report_tasks[task_id]["status"] = "error"
        report_tasks[task_id]["error"] = str(e)
        report_tasks[task_id]["traceback"] = traceback.format_exc()
        report_tasks[task_id]["status_details"] = error_message

# Add new LangChain search endpoint
@router.post("/search-with-langchain")
async def search_with_langchain(query: str, max_results: int = 5):
    """
    Search the web using LangChain, extract content from web pages,
    and provide summaries of the content.
    """
    if not LANGCHAIN_AGENT_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="LangChain search agent is not available. Please install required packages."
        )
    
    try:
        # Initialize the LangChain search agent
        agent = LangChainSearchAgent()
        
        # Process the query
        results = agent.process_query(query)
        
        # Limit the number of results
        if "search_results" in results:
            results["search_results"] = results["search_results"][:max_results]
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error performing LangChain search: {str(e)}"
        )

# Add background task for LangChain search
class LangChainSearchRequest(BaseModel):
    query: str = Field(..., min_length=5, description="The search query")
    max_results: int = Field(5, description="Maximum number of results to return")

@router.post("/background-langchain-search")
async def background_langchain_search(request: LangChainSearchRequest, background_tasks: BackgroundTasks):
    """
    Start a background task to search with LangChain and extract/summarize content.
    """
    task_id = f"langchain_search_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(request.query) % 10000}"
    
    # Store task
    if not hasattr(router, 'langchain_tasks'):
        router.langchain_tasks = {}
    
    router.langchain_tasks[task_id] = {
        "status": "pending",
        "query": request.query,
        "start_time": datetime.now().isoformat(),
        "message": "LangChain search started",
        "progress": 0
    }
    
    # Start background task
    background_tasks.add_task(
        run_langchain_search,
        task_id=task_id,
        query=request.query,
        max_results=request.max_results
    )
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": f"LangChain search started for: {request.query}"
    }

@router.get("/langchain-search-status/{task_id}")
async def get_langchain_search_status(task_id: str):
    """Check the status of a LangChain search task."""
    if not hasattr(router, 'langchain_tasks') or task_id not in router.langchain_tasks:
        raise HTTPException(status_code=404, detail=f"LangChain search task {task_id} not found")
    
    return router.langchain_tasks[task_id]

@router.get("/langchain-search-result/{task_id}")
async def get_langchain_search_result(task_id: str):
    """Get the result of a completed LangChain search task."""
    if not hasattr(router, 'langchain_tasks') or task_id not in router.langchain_tasks:
        raise HTTPException(status_code=404, detail=f"LangChain search task {task_id} not found")
    
    task = router.langchain_tasks[task_id]
    
    if task["status"] != "completed":
        return {
            "task_id": task_id,
            "status": task["status"],
            "message": "Search still in progress",
            "progress": task.get("progress", 0)
        }
    
    return task["result"]

def run_langchain_search(task_id: str, query: str, max_results: int):
    """Run the LangChain search process in the background."""
    tasks = router.langchain_tasks
    
    try:
        # Update task status
        tasks[task_id]["status_details"] = "Initializing LangChain search..."
        tasks[task_id]["progress"] = 0.1
        
        # Check if LangChain agent is available
        if not LANGCHAIN_AGENT_AVAILABLE:
            raise Exception("LangChain search agent is not available")
        
        # Initialize the LangChain search agent
        agent = LangChainSearchAgent()
        
        # Update status
        tasks[task_id]["status_details"] = "Performing web search..."
        tasks[task_id]["progress"] = 0.2
        
        # Process the query
        results = agent.process_query(query)
        
        # Update status 
        tasks[task_id]["status_details"] = "Processing search results..."
        tasks[task_id]["progress"] = 0.7
        
        # Limit the number of results
        if "search_results" in results:
            results["search_results"] = results["search_results"][:max_results]
        
        # Update task with result
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = results
        tasks[task_id]["completion_time"] = datetime.now().isoformat()
        tasks[task_id]["progress"] = 1.0
        tasks[task_id]["status_details"] = "LangChain search completed successfully"
        
    except Exception as e:
        import traceback
        error_message = f"Error in LangChain search: {str(e)}"
        tasks[task_id]["status"] = "error"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["traceback"] = traceback.format_exc()
        tasks[task_id]["status_details"] = error_message
