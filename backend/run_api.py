"""
Simple script to start the FastAPI application with uvicorn
and perform a basic self-check to ensure the API is responding.
"""
import os
import sys
import time
import requests
import uvicorn
import threading
import webbrowser

def check_api(base_url="http://127.0.0.1:8000", retries=5, delay=1):
    """Check if the API is running by hitting the health endpoint."""
    for attempt in range(retries):
        try:
            print(f"Checking API health (attempt {attempt+1}/{retries})...")
            response = requests.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ API is running and healthy!")
                print(f"Response: {response.json()}")
                return True
            else:
                print(f"API returned status code: {response.status_code}")
        except requests.RequestException as e:
            print(f"Error connecting to API: {str(e)}")
        
        if attempt < retries - 1:
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
    
    print("❌ Could not connect to API after multiple attempts")
    return False

def filter_dynamic_websites(urls, query, min_sites=6):
    """Filter and rank dynamic websites related to the prompted text, ensuring a minimum number of sites.
    
    Args:
        urls: List of URL dictionaries with 'url' and possibly 'title', 'snippet' keys
        query: The user's search query/prompt
        min_sites: Minimum number of unique websites to return (default: 6)
    
    Returns:
        List of filtered and ranked URL dictionaries
    """
    print(f"Enhanced filtering for query: '{query}', targeting {min_sites} unique websites")
    
    # Process query to extract important terms
    query_terms = _extract_key_terms(query)
    print(f"Key terms extracted: {', '.join(query_terms)}")
    
    # Initial scoring of URLs
    scored_urls = []
    domain_map = {}  # Track URLs by domain for better filtering
    
    for url_data in urls:
        url = url_data['url']
        title = url_data.get('title', '')
        snippet = url_data.get('snippet', '')
        
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Get base domain (e.g., example.com from www.example.com)
            base_domain = _get_base_domain(domain)
            
            # Calculate relevance score
            score = _calculate_url_relevance(url, title, snippet, query_terms)
            
            # Create enhanced resource object
            resource = {
                'url': url,
                'title': title,
                'snippet': snippet,
                'domain': domain,
                'base_domain': base_domain,
                'score': score,
                'path_depth': len([p for p in parsed_url.path.split('/') if p])
            }
            
            # Group by base domain for diversity filtering
            if base_domain not in domain_map:
                domain_map[base_domain] = []
            domain_map[base_domain].append(resource)
            
            # Also add to scored list
            scored_urls.append(resource)
            
        except Exception as e:
            print(f"Error processing URL {url}: {str(e)}")
    
    # Sort all URLs by score
    scored_urls.sort(key=lambda x: x['score'], reverse=True)
    
    # First pass - take the best URL from each domain until we have enough
    filtered_resources = []
    used_domains = set()
    
    # Sort domains by their best score
    sorted_domains = sorted(
        domain_map.items(),
        key=lambda x: max(res['score'] for res in x[1]),
        reverse=True
    )
    
    # First select the top scoring URL from top domains
    for domain, resources in sorted_domains:
        if domain in used_domains:
            continue
            
        # Take the highest scoring URL from this domain
        best_resource = max(resources, key=lambda x: x['score'])
        filtered_resources.append(best_resource)
        used_domains.add(domain)
        
        # If we have enough unique domains, stop
        if len(filtered_resources) >= min_sites:
            break
    
    # If we don't have enough resources yet, add more but avoid overrepresentation
    if len(filtered_resources) < min_sites:
        # Consider domains we've used but might have additional good resources
        for domain, resources in sorted_domains:
            if len(filtered_resources) >= min_sites:
                break
                
            # Skip if no resources left for this domain
            domain_resources = [r for r in resources if r not in filtered_resources]
            if not domain_resources:
                continue
                
            # Only add a second resource from a domain if it's high quality
            best_remaining = max(domain_resources, key=lambda x: x['score'])
            if best_remaining['score'] >= 5:  # Only add if score is good
                filtered_resources.append(best_remaining)
    
    # Final sort by score
    filtered_resources.sort(key=lambda x: x['score'], reverse=True)
    
    # Limit to the best resources but ensure minimum count
    result = filtered_resources[:max(min_sites, 10)]
    
    print(f"Enhanced filtering complete - found {len(result)} quality websites from {len(domain_map)} domains")
    return result

def _extract_key_terms(query):
    """Extract important terms from a query."""
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                 'with', 'about', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
                 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall', 
                 'should', 'may', 'might', 'must', 'can', 'could', 'of'}
    
    # Convert to lowercase and clean punctuation
    import re
    clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
    
    # Extract terms, filtering stop words and short terms
    terms = [term for term in clean_query.split() 
            if term not in stop_words and len(term) > 2]
    
    return terms

def _get_base_domain(domain):
    """Extract the base domain from a full domain."""
    parts = domain.split('.')
    
    # Handle special cases like co.uk, com.au
    if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net', 'edu', 'gov', 'ac']:
        return '.'.join(parts[-3:])
        
    # Standard case
    if len(parts) > 1:
        return '.'.join(parts[-2:])
        
    return domain

def _calculate_url_relevance(url, title, snippet, query_terms):
    """Calculate a relevance score for a URL based on query terms."""
    from urllib.parse import urlparse
    
    score = 0
    
    # Get domain and path
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    path = parsed_url.path.lower()
    
    # Check domain quality - prefer educational and authoritative sources
    if domain.endswith('.edu'):
        score += 12
    elif domain.endswith('.gov'):
        score += 10
    elif domain.endswith('.org'):
        score += 8
    elif 'wikipedia.org' in domain:
        score += 9
    elif any(term in domain for term in ['research', 'science', 'academic', 'journal']):
        score += 7
    elif any(term in domain for term in ['papers', 'data', 'report', 'study']):
        score += 5
        
    # Penalize domains that are less likely to be good for research
    if any(term in domain for term in ['pinterest', 'instagram', 'facebook', 'twitter', 'tiktok']):
        score -= 10
        
    # Check title relevance (highest importance)
    if title:
        title_lower = title.lower()
        exact_phrase_match = 0
        term_matches = 0
        
        # Check for exact phrase match in title
        if ' '.join(query_terms) in title_lower:
            exact_phrase_match = 15
        
        # Check for individual term matches
        for term in query_terms:
            if term in title_lower:
                term_matches += 4
        
        # Use the better of the two scores
        score += max(exact_phrase_match, term_matches)
        
    # Check snippet relevance (medium importance)
    if snippet:
        snippet_lower = snippet.lower()
        for term in query_terms:
            if term in snippet_lower:
                score += 3
                
    # Check URL path relevance (lower importance)
    for term in query_terms:
        if term in path:
            score += 2
            
    # Avoid certain types of pages that are unlikely to contain good research info
    if any(pat in path.lower() for pat in ['/login', '/signup', '/account', '/cart', '/checkout']):
        score -= 20
        
    # Prefer paths that suggest content pages
    if any(pat in path.lower() for pat in ['/article', '/paper', '/research', '/study', '/report', '/publication']):
        score += 5
        
    return score

def extract_relevant_urls(base_url, query, max_urls=3):
    """From a website, extract URLs that are most relevant to the query.
    
    Args:
        base_url: URL of the website to extract links from
        query: The user's search query
        max_urls: Maximum number of URLs to return
        
    Returns:
        List of the most relevant URLs from the website
    """
    print(f"Extracting relevant URLs from {base_url} for query: {query}")
    
    try:
        # Get the page content
        response = requests.get(base_url, timeout=10)
        if response.status_code != 200:
            print(f"Failed to access {base_url}: status code {response.status_code}")
            return []
            
        # Use BeautifulSoup to parse the HTML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract all links
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Make absolute URLs
            if href.startswith('/'):
                from urllib.parse import urljoin
                href = urljoin(base_url, href)
                
            # Skip external links, anchors, javascript, etc.
            if not href.startswith('http') or "#" in href or "javascript:" in href:
                continue
                
            # Skip certain URL patterns
            from urllib.parse import urlparse
            if any(x in urlparse(href).path.lower() for x in ['/login', '/signup', '/account', '/cart']):
                continue
                
            # Check if it's from the same domain
            base_domain = urlparse(base_url).netloc
            link_domain = urlparse(href).netloc
            if base_domain != link_domain:
                continue
                
            # Get link text if available
            link_text = a_tag.text.strip()
            
            links.append({
                'url': href,
                'text': link_text
            })
        
        # Score links based on relevance to query
        query_terms = [term.lower() for term in query.split() if len(term) > 3]
        
        scored_links = []
        for link in links:
            score = 0
            
            # Check link text relevance
            if link['text']:
                for term in query_terms:
                    if term in link['text'].lower():
                        score += 3
                        
            # Check URL path relevance
            from urllib.parse import urlparse
            path = urlparse(link['url']).path.lower()
            for term in query_terms:
                if term in path:
                    score += 2
                    
            # Prefer deeper links (more specific content)
            path_depth = len([p for p in path.split('/') if p])
            score += min(path_depth, 3)  # Cap at 3 to avoid over-weighting
            
            scored_links.append({
                'url': link['url'],
                'text': link['text'],
                'score': score
            })
        
        # Sort by score and take top results
        scored_links.sort(key=lambda x: x['score'], reverse=True)
        best_links = [link['url'] for link in scored_links[:max_urls]]
        
        print(f"Found {len(best_links)} relevant URLs from {base_url}")
        return best_links
        
    except Exception as e:
        print(f"Error extracting links from {base_url}: {str(e)}")
        return []

def test_research_endpoint(base_url="http://127.0.0.1:8000", query="Quantum Computing"):
    """Test the research API endpoint with improved web source filtering."""
    try:
        print(f"\nTesting research API with improved URL retrieval for: '{query}'...")
        
        # First, ensure our URL retriever works independently
        from app.services.url_retriever import URLRetriever
        import asyncio
        
        # Test the URL retriever directly
        print("\nTesting direct URL retrieval...")
        urls = asyncio.run(URLRetriever.get_diverse_urls(query, min_urls=7))
        
        print(f"\nDirect URL retriever found {len(urls)} relevant websites:")
        for i, url_data in enumerate(urls):
            print(f"\n{i+1}. {url_data.get('title', 'Untitled')}")
            print(f"   URL: {url_data.get('url')}")
            print(f"   Source: {url_data.get('source')}")
            print(f"   Score: {url_data.get('relevance_score')}")
        
        # Now test through the API
        # ...existing API test code...

    except Exception as e:
        print(f"❌ Error testing research endpoint: {str(e)}")
        return False

def run_server():
    """Start the uvicorn server with the FastAPI app."""
    # Add support for diverse web sources
    add_web_source_providers()
    
    # Set PYTHONPATH to ensure imports work correctly
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("python-dotenv not installed, skipping .env loading")
    
    # Start the server
    print("Starting FastAPI server...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

def add_web_source_providers():
    """Configure and add multiple web source providers for more comprehensive results."""
    try:
        from app.services.web_source_service import WebSourceService
        
        # Register multiple search providers to ensure we get diverse results
        WebSourceService.register_provider("serpapi", priority=1)
        WebSourceService.register_provider("ddg", priority=2)  # DuckDuckGo
        WebSourceService.register_provider("google_custom", priority=3)
        WebSourceService.register_provider("web_scraper", priority=4)
        
        # Configure minimum results settings
        WebSourceService.set_config({
            "min_sources": 7,                  # Minimum number of sources to return
            "min_domains": 6,                  # Minimum number of unique domains
            "use_fallback_providers": True,    # Try additional providers if primary fails
            "allow_dynamic_content": True,     # Include websites that might have dynamic content
            "max_retries": 3,                  # Number of search retries if results are insufficient
            "cross_reference_results": True,   # Cross-reference results across providers
        })
        
        print("✅ Configured multiple web source providers for comprehensive research")
    except Exception as e:
        print(f"⚠️ Could not configure web source providers: {str(e)}")

def open_browser():
    """Open the browser to the API documentation after a delay."""
    time.sleep(2)  # Wait for server to start
    webbrowser.open("http://127.0.0.1:8000/docs")
    print("\nOpened browser to API documentation")
    
    # Also run API tests
    time.sleep(1)
    check_api()
    test_research_endpoint()

if __name__ == "__main__":
    # Add URL retriever initialization before starting the server
    print("Initializing enhanced URL retrieval service...")
    try:
        from app.services.url_retriever import URLRetriever
        print("✅ URL retriever service initialized")
    except Exception as e:
        print(f"⚠️ URL retriever initialization error: {str(e)}")
    
    # Start browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run the server (this will block until server stops)
    run_server()
