"""
Routes for search functionality with dynamic web results.
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus
import re
import time
import os  # Add this import for os.getenv

# Import search functionality
from app.agents.web_search_agent import WebSearchAgent
from app.services.search_service import SearchService

# Create router
router = APIRouter()

# Define request and response models
class SearchRequest(BaseModel):
    query: str
    sources: Optional[List[str]] = None
    relevanceThreshold: Optional[float] = 0.7
    maxResults: Optional[int] = 10
    excludeDomains: Optional[List[str]] = None
    mustIncludeTerms: Optional[List[str]] = None

class SearchResult(BaseModel):
    title: str
    link: str
    snippet: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    success: bool = True
    message: str = "Search completed successfully"

class QueryAnalysisRequest(BaseModel):
    query: str

class QueryAnalysisResponse(BaseModel):
    categories: List[Dict[str, Any]]
    recommended: List[str]

@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Perform a direct web search based on the user's query and return the results
    that specifically match the prompt content.
    """
    try:
        # Validate input
        if not request.query or len(request.query.strip()) < 3:
            raise HTTPException(status_code=400, detail="Query must be at least 3 characters long")
        
        # Initialize web search agent
        search_agent = WebSearchAgent()
        
        # Extract key terms from the query for content matching
        query_terms = extract_key_terms(request.query)
        print(f"Extracted key terms: {query_terms}")
        
        # Define must-include terms if specified
        must_include = request.mustIncludeTerms or []
        if len(must_include) == 0 and len(query_terms) > 0:
            # Use the most important terms from the query if none specified
            must_include = query_terms[:3]  # Use top 3 terms
        
        # Perform search
        raw_results = search_agent.search_web(request.query, num_results=max(15, request.maxResults * 2))
        
        # In-depth content analysis and filtering
        detailed_results = []
        
        for i, result in enumerate(raw_results):
            # Skip if we've already found enough high-quality results
            if len(detailed_results) >= request.maxResults:
                break
                
            url = result.get('url')
            if not url:
                continue
                
            # Skip excluded domains if specified
            if request.excludeDomains and any(domain in url for domain in request.excludeDomains):
                continue
            
            try:
                # Extract and analyze content from the webpage
                content = extract_and_analyze_content(
                    url, 
                    query_terms, 
                    must_include_terms=must_include,
                    relevance_threshold=request.relevanceThreshold
                )
                
                if content and content['relevance_score'] >= request.relevanceThreshold:
                    # Add to results with enhanced information
                    detailed_results.append({
                        'title': result.get('title', 'No title'),
                        'link': url,
                        'snippet': content.get('summary', result.get('snippet', 'No description available')),
                        'relevance': content['relevance_score'],
                        'matching_terms': content['matching_terms'],
                        'content_type': content['content_type'],
                        'domain_category': categorize_domain(url)
                    })
            except Exception as extract_error:
                print(f"Error extracting content from {url}: {str(extract_error)}")
        
        # Sort by relevance
        detailed_results.sort(key=lambda x: x['relevance'], reverse=True)
        
        # Format results
        formatted_results = []
        for i, result in enumerate(detailed_results[:request.maxResults]):
            # Format the snippet to highlight matching terms
            highlighted_snippet = highlight_matching_terms(
                result['snippet'], 
                query_terms + must_include
            )
            
            # Create the formatted result
            formatted_results.append(
                SearchResult(
                    title=result['title'],
                    link=result['link'],
                    snippet=f"{highlighted_snippet} [Relevance: {result['relevance']:.2f}]"
                )
            )
        
        return SearchResponse(
            results=formatted_results,
            message=f"Found {len(formatted_results)} relevant results that match your query content"
        )
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error performing search: {str(e)}"
        )

def extract_key_terms(query: str) -> List[str]:
    """Extract important terms from the query."""
    # Remove common stop words
    stop_words = {
        'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'about',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'shall', 'should', 'can', 'could',
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how'
    }
    
    # Clean query and tokenize
    clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
    words = [word for word in clean_query.split() if word not in stop_words and len(word) > 2]
    
    # Count word frequency
    word_freq = {}
    for word in words:
        if word in word_freq:
            word_freq[word] += 1
        else:
            word_freq[word] = 1
    
    # Sort words by frequency, then by length (prefer longer words)
    sorted_words = sorted(word_freq.items(), key=lambda x: (x[1], len(x[0])), reverse=True)
    
    # Return just the words
    return [word for word, _ in sorted_words]

def highlight_matching_terms(text: str, terms: List[str]) -> str:
    """Highlight matching terms in the text."""
    for term in terms:
        # Create a case-insensitive pattern
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        # Replace with bold version
        text = pattern.sub(f"**{term.upper()}**", text)
    return text

def extract_and_analyze_content(url: str, query_terms: List[str], must_include_terms: List[str] = None, relevance_threshold: float = 0.5) -> Dict[str, Any]:
    """
    Extract content from URL and analyze it for relevance to the query.
    """
    try:
        # Set up headers
        headers = {
            'User-Agent': os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/'
        }
        
        # Make request with timeout
        response = requests.get(url, headers=headers, timeout=10)
        content_type = response.headers.get('Content-Type', '')
        
        # Determine content type
        if 'text/html' in content_type:
            doc_type = 'html'
        elif 'application/pdf' in content_type:
            doc_type = 'pdf'
        elif 'application/json' in content_type:
            doc_type = 'json'
        else:
            doc_type = 'other'
        
        # Extract text content based on content type
        if doc_type == 'html':
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            # Try to find main content
            main_content = None
            for selector in ['article', 'main', '.content', '#content', '.post', '.entry-content']:
                content_elem = soup.select_one(selector)
                if content_elem:
                    main_content = content_elem
                    break
            
            # Use body if no main content found
            if not main_content:
                main_content = soup.body
            
            # Extract paragraphs and headings
            paragraphs = []
            for tag in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = tag.get_text().strip()
                if len(text) > 20:  # Skip very short paragraphs
                    paragraphs.append(text)
            
            # Join paragraphs with spacing
            content_text = "\n\n".join(paragraphs)
            
            # Create a summary (first 3 paragraphs)
            summary = "\n".join(paragraphs[:3]) if paragraphs else ""
        else:
            # For non-HTML content, use a placeholder
            content_text = f"This is a {doc_type.upper()} document. Content extraction not supported."
            summary = content_text
        
        # Calculate relevance score
        relevance_score = 0.0
        max_possible_score = len(query_terms)
        matching_terms = []
        
        # Check for must-include terms
        if must_include_terms and not any(term.lower() in content_text.lower() for term in must_include_terms):
            # If must-include terms are specified but none are found, return low relevance
            return {
                'content': content_text[:500],
                'summary': summary[:300],
                'relevance_score': 0.1,
                'matching_terms': [],
                'content_type': doc_type
            }
        
        # Score based on query terms
        for term in query_terms:
            if term.lower() in content_text.lower():
                relevance_score += 1
                matching_terms.append(term)
        
        # Normalize score
        if max_possible_score > 0:
            relevance_score = relevance_score / max_possible_score
        
        # Boost score if URL contains query terms
        url_lower = url.lower()
        for term in query_terms:
            if term.lower() in url_lower:
                relevance_score += 0.1
                relevance_score = min(relevance_score, 1.0)  # Cap at 1.0
        
        return {
            'content': content_text[:500],  # Truncate for efficiency
            'summary': summary[:300],  # Truncated summary
            'relevance_score': relevance_score,
            'matching_terms': matching_terms,
            'content_type': doc_type
        }
        
    except Exception as e:
        print(f"Error extracting content from {url}: {str(e)}")
        return None

def categorize_domain(url: str) -> str:
    """Categorize the domain type based on URL patterns."""
    domain = urlparse(url).netloc.lower()
    
    # Academic and research domains
    if any(pattern in domain for pattern in ['.edu', '.ac.', 'research', 'science', 'scholar', 'academic']):
        return 'academic'
    
    # News and media sites
    elif any(pattern in domain for pattern in ['news', 'cnn', 'bbc', 'nyt', 'reuters', 'npr', 'guardian']):
        return 'news'
    
    # Government sites
    elif any(pattern in domain for pattern in ['.gov', '.mil', 'government']):
        return 'government'
    
    # Technical documentation
    elif any(pattern in domain for pattern in ['docs.', 'developer.', 'api.', 'github', 'stackoverflow']):
        return 'technical'
    
    # Online courses and educational content
    elif any(pattern in domain for pattern in ['course', 'learn', 'tutorial', 'khan', 'udemy', 'coursera']):
        return 'educational'
    
    # Scientific and medical content
    elif any(pattern in domain for pattern in ['science', 'medical', 'health', 'nih.', 'who.', 'nature']):
        return 'scientific'
    
    # Encyclopedia and reference sites
    elif any(pattern in domain for pattern in ['wikipedia', 'encyclopedia', 'britannica']):
        return 'reference'
    
    # Blogs and opinion sites
    elif any(pattern in domain for pattern in ['blog', 'medium.com', 'wordpress', 'blogger']):
        return 'blog'
    
    # Default category
    return 'general'

# Update the analyze-query endpoint to include domain categorization
@router.post("/analyze-query", response_model=QueryAnalysisResponse)
async def analyze_query(request: QueryAnalysisRequest):
    """
    Analyze a query to determine relevant source categories.
    """
    try:
        # Validate input
        if not request.query or len(request.query.strip()) < 3:
            raise HTTPException(status_code=400, detail="Query must be at least 3 characters long")
        
        query = request.query.lower()
        
        # Define our source categories
        all_categories = [
            {"id": "general", "name": "General Knowledge", "recommended": False},
            {"id": "academic", "name": "Academic Research", "recommended": False},
            {"id": "news", "name": "News & Current Events", "recommended": False},
            {"id": "technical", "name": "Technical Documentation", "recommended": False},
            {"id": "scientific", "name": "Scientific Publications", "recommended": False},
            {"id": "educational", "name": "Educational Resources", "recommended": False},
            {"id": "government", "name": "Government Sources", "recommended": False},
            {"id": "books", "name": "Books & Literature", "recommended": False},
        ]
        
        # Define keyword patterns for each category
        patterns = {
            "academic": [
                "research", "study", "paper", "journal", "thesis", "dissertation",
                "academic", "science", "theory", "analysis", "experiment", "methodology"
            ],
            "news": [
                "news", "current", "recent", "update", "today", "latest", "report",
                "politics", "event", "development", "crisis", "breaking"
            ],
            "technical": [
                "code", "programming", "software", "hardware", "documentation", "framework",
                "algorithm", "api", "interface", "library", "function", "tool"
            ],
            "scientific": [
                "science", "scientific", "biology", "chemistry", "physics", "astronomy",
                "medicine", "medical", "climate", "experiment", "laboratory"
            ],
            "educational": [
                "learn", "course", "tutorial", "education", "lesson", "teach",
                "training", "curriculum", "school", "university", "college"
            ],
            "government": [
                "government", "policy", "regulation", "law", "legislation", "federal",
                "state", "agency", "public", "official", "administration"
            ],
            "books": [
                "book", "author", "literature", "novel", "fiction", "biography",
                "history", "historical", "literary", "chapter", "publication"
            ]
        }
        
        # Determine which categories match the query
        recommended_categories = ["general"]  # Always include general
        
        for category, keywords in patterns.items():
            if any(keyword in query for keyword in keywords):
                recommended_categories.append(category)
        
        # Mark recommended categories
        for category in all_categories:
            category["recommended"] = category["id"] in recommended_categories
        
        # Try to use LLM for better categorization if available
        try:
            from openai import OpenAI
            client = OpenAI()
            
            # Get better category recommendations with AI
            prompt = f"""
            Analyze this search query: "{request.query}"
            
            Which of these information source categories would be most relevant for this query?
            - general: General knowledge websites like Wikipedia
            - academic: Academic papers, research studies, scholarly sources
            - news: News articles, current events, recent developments
            - technical: Technical documentation, programming resources, developer guides
            - scientific: Scientific publications, research data, experimental findings
            - educational: Educational resources, tutorials, learning materials
            - government: Government documents, policies, regulations, public data
            - books: Books, literature, historical texts
            
            Return only the category IDs as a JSON array of strings, with the most relevant first.
            Example: ["academic", "scientific", "general"]
            """
            
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a search query analyzer that helps determine the best information sources."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=100
            )
            
            # Extract and parse the response
            ai_categories = []
            try:
                import json
                ai_text = completion.choices[0].message.content.strip()
                
                # Extract JSON array if wrapped in other text
                if '[' in ai_text and ']' in ai_text:
                    start = ai_text.find('[')
                    end = ai_text.rfind(']') + 1
                    ai_text = ai_text[start:end]
                
                ai_categories = json.loads(ai_text)
                
                # Use AI recommendations if available
                if ai_categories and len(ai_categories) > 0:
                    recommended_categories = ai_categories
            except Exception as json_error:
                print(f"Error parsing AI response: {str(json_error)}")
        
        except Exception as llm_error:
            print(f"Error using LLM for categorization: {str(llm_error)}")
            # Continue with the keyword-based categories
        
        return {
            "categories": all_categories,
            "recommended": recommended_categories
        }
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error analyzing query: {str(e)}"
        )

@router.post("/search", response_model=SearchResponse)
async def search_service(request: SearchRequest):
    """Search for information on a topic using real-time web results."""
    results = await SearchService.search_query(query=request.query, min_results=request.maxResults)
    
    return {
        "results": results,
        "query": request.query,
        "total_found": len(results)
    }

@router.get("/search", response_model=SearchResponse)
async def search_service_get(
    query: str = Query(..., min_length=2),
    num_results: int = Query(10, ge=1, le=50)
):
    """Search endpoint for GET requests."""
    results = await SearchService.search_query(query=query, min_results=num_results)
    
    return {
        "results": results,
        "query": query,
        "total_found": len(results)
    }

@router.post("/enhanced-search")
async def enhanced_search(request: SearchRequest):
    """Get enhanced search results with categorized information."""
    results = await SearchService.get_enhanced_search_results(query=request.query)
    
    return results
