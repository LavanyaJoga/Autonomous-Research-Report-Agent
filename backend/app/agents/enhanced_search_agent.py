"""
Enhanced web search agent that combines results from multiple search providers
and implements better filtering/ranking for higher quality results.
"""

import os
import time
import json
import re
import random
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EnhancedWebSearchAgent:
    """Enhanced web search agent that combines results from multiple search providers."""
    
    def __init__(self):
        """Initialize the web search agent with API keys and configuration."""
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        self.results_cache = {}  # Cache search results
        self.last_search_time = 0  # Timestamp of last search to prevent rate limiting
        
        # Define search providers
        self.search_providers = [
            self._search_serpapi,
            self._search_duckduckgo,
            self._search_bing,
            self._search_google_direct
        ]
    
    def search_web(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Search the web for information related to a query.
        
        Args:
            query: The search query
            num_results: Number of search results to return
            
        Returns:
            List of search result dictionaries
        """
        # Rate limiting - ensure at least 1 second between searches
        current_time = time.time()
        if current_time - self.last_search_time < 1:
            time.sleep(1 - (current_time - self.last_search_time))
        self.last_search_time = time.time()
        
        # Check cache first
        cache_key = f"{query}_{num_results}"
        if cache_key in self.results_cache:
            print(f"Cache hit for query: {query}")
            return self.results_cache[cache_key]
        
        # Try each search provider until we get results
        all_results = []
        for provider in self.search_providers:
            try:
                results = provider(query, num_results)
                if results:
                    all_results.extend(results)
                    if len(all_results) >= num_results:
                        break
            except Exception as e:
                print(f"Error with search provider: {str(e)}")
        
        # If we still don't have enough results, try a fallback
        if len(all_results) < num_results:
            fallback_results = self._generate_fallback_results(query, num_results - len(all_results))
            all_results.extend(fallback_results)
        
        # Filter for duplicates based on URL
        unique_results = []
        seen_urls = set()
        
        for result in all_results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
                
                # Add query source information
                result['query'] = query
        
        # Cache results
        final_results = unique_results[:num_results]
        self.results_cache[cache_key] = final_results
        
        return final_results
    
    def multi_query_search(self, main_query: str, num_results: int = 10) -> List[Dict]:
        """
        Generate multiple search queries based on the main query and search with each.
        
        Args:
            main_query: The main research query
            num_results: Total number of results to return
            
        Returns:
            Combined search results from all queries
        """
        # Generate variations of the query for more diverse results
        variations = self._generate_query_variations(main_query)
        
        all_results = []
        seen_urls = set()
        
        # Limit per-query results based on how many variations we have
        per_query_limit = max(5, num_results // len(variations))
        
        # Search with each query variation
        for query_var in variations:
            try:
                # Add the query variation to differentiate sources
                results = self.search_web(query_var, per_query_limit)
                
                # Track which variation found each result
                for result in results:
                    result['query'] = query_var
                    
                    # Check for duplicates
                    if result['url'] not in seen_urls:
                        seen_urls.add(result['url'])
                        all_results.append(result)
            except Exception as e:
                print(f"Error searching with query variation '{query_var}': {str(e)}")
        
        # Filter and rank the combined results
        from app.main import filter_and_rank_web_resources
        ranked_results = filter_and_rank_web_resources(all_results, main_query, max_results=num_results)
        
        return ranked_results
    
    def _generate_query_variations(self, query: str) -> List[str]:
        """Generate variations of the query for more diverse search results."""
        variations = [query]  # Always include the original query
        
        # Remove question markers and common question starts
        clean_query = re.sub(r'[?!]', '', query)
        clean_query = re.sub(r'^(what is|tell me about|how does|who is|when was|where is|why is)\s+', '', clean_query, flags=re.IGNORECASE)
        
        # Add query variations
        variations.extend([
            f"best resources about {clean_query}",
            f"{clean_query} explained",
            f"{clean_query} academic research",
            f"{clean_query} tutorial"
        ])
        
        return variations[:5]  # Limit to 5 variations including the original
    
    def _search_serpapi(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search the web using SerpAPI."""
        if not self.serpapi_key:
            return []
            
        try:
            url = f"https://serpapi.com/search.json?q={quote_plus(query)}&num={num_results}&api_key={self.serpapi_key}"
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                print(f"Error from SerpAPI: {response.status_code} - {response.text}")
                return []
                
            data = response.json()
            
            # Extract organic results
            results = []
            if 'organic_results' in data:
                for item in data['organic_results'][:num_results]:
                    results.append({
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', '')
                    })
            
            return results
            
        except Exception as e:
            print(f"SerpAPI search error: {str(e)}")
            return []
    
    def _search_duckduckgo(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search using DuckDuckGo."""
        try:
            # DuckDuckGo doesn't have an official API, but we can use the lite version
            url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
            
            headers = {
                'User-Agent': self.user_agent
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return []
            
            # Very basic parsing of the HTML response
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            # This is a simplified parser and might break if DuckDuckGo changes their HTML
            for a_tag in soup.select('.result-link a'):
                title = a_tag.get_text().strip()
                href = a_tag.get('href', '')
                
                # Find corresponding snippet
                snippet = ""
                snippet_tag = a_tag.find_next('td', class_='result-snippet')
                if snippet_tag:
                    snippet = snippet_tag.get_text().strip()
                
                if href and title:
                    results.append({
                        'title': title,
                        'url': href,
                        'snippet': snippet
                    })
                    
                if len(results) >= num_results:
                    break
            
            return results
            
        except Exception as e:
            print(f"DuckDuckGo search error: {str(e)}")
            return []
    
    def _search_bing(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search using Bing."""
        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}&count={num_results}"
            
            headers = {
                'User-Agent': self.user_agent
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return []
            
            # Parse the HTML response
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            # Look for search result items
            for result in soup.select('li.b_algo'):
                title_tag = result.select_one('h2 a')
                if title_tag:
                    title = title_tag.get_text().strip()
                    href = title_tag.get('href', '')
                    
                    # Find snippet
                    snippet = ""
                    snippet_tag = result.select_one('.b_caption p')
                    if snippet_tag:
                        snippet = snippet_tag.get_text().strip()
                    
                    if href and title:
                        results.append({
                            'title': title,
                            'url': href,
                            'snippet': snippet
                        })
                
                if len(results) >= num_results:
                    break
            
            return results
            
        except Exception as e:
            print(f"Bing search error: {str(e)}")
            return []
    
    def _search_google_direct(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search using direct Google queries."""
        try:
            url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}"
            
            # Use a more browser-like user agent to avoid blocks
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return []
            
            # Parse the HTML response
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            # Look for Google search result divs
            for result in soup.select('div.g'):
                # Title and URL
                title_tag = result.select_one('h3')
                link_tag = result.select_one('a')
                
                if title_tag and link_tag:
                    title = title_tag.get_text().strip()
                    href = link_tag.get('href', '')
                    
                    # Skip non-http links
                    if not href.startswith('http'):
                        continue
                    
                    # Snippet
                    snippet = ""
                    snippet_tag = result.select_one('div.VwiC3b')
                    if snippet_tag:
                        snippet = snippet_tag.get_text().strip()
                    
                    if href and title:
                        results.append({
                            'title': title,
                            'url': href,
                            'snippet': snippet
                        })
                
                if len(results) >= num_results:
                    break
            
            return results
            
        except Exception as e:
            print(f"Google direct search error: {str(e)}")
            return []
    
    def _generate_fallback_results(self, query: str, count: int) -> List[Dict]:
        """Generate reliable fallback results for a query when search APIs fail."""
        # Import the get_reliable_resources function
        from app.main import get_reliable_resources
        
        return get_reliable_resources(query, count)
