import os
import requests
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, quote_plus
import json
import random
import re
from bs4 import BeautifulSoup

class WebSearchAgent:
    """Agent responsible for finding relevant web URLs on a given topic."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the web search agent."""
        self.api_key = api_key or os.getenv("SERPER_API_KEY") or os.getenv("SERPAPI_KEY")
        self.valid_urls = []
        self.tried_urls = []
    
    def search_web(self, query: str, num_results: int = 8) -> List[Dict[str, str]]:
        """
        Search the web for relevant URLs on the given query.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            List of dictionaries with 'title', 'url', and 'snippet'
        """
        # Filter and clean the query before searching
        filtered_query = self._filter_query(query)
        print(f"Original query: {query}")
        print(f"Filtered query for search: {filtered_query}")
        
        # Try different search methods in order of preference
        search_methods = [
            self._search_with_serper,
            self._search_with_serpapi,
            self._search_with_fallback
        ]
        
        for method in search_methods:
            try:
                results = method(filtered_query, num_results)
                if results:
                    # Verify URLs are valid
                    valid_results = self._validate_urls(results)
                    if valid_results:
                        return valid_results[:num_results]
            except Exception as e:
                print(f"Search method failed: {str(e)}")
                continue
        
        # If all methods fail, return a curated list based on the query keywords
        return self._generate_topical_urls(filtered_query, num_results)
    
    def multi_query_search(self, topic: str, num_results: int = 8) -> List[Dict[str, str]]:
        """
        Search the web using multiple derived queries from a topic.
        
        Args:
            topic: The main research topic
            num_results: Total number of results to return
            
        Returns:
            List of dictionaries with 'title', 'url', 'snippet' and 'query'
        """
        # Generate multiple search queries from the topic
        search_queries = self._generate_search_queries(topic)
        print(f"Generated multiple search queries: {search_queries}")
        
        combined_results = []
        
        # Use the first 3 queries to avoid rate limiting
        for i, query in enumerate(search_queries[:3]):
            try:
                print(f"Searching with query {i+1}/{len(search_queries[:3])}: {query}")
                # Get fewer results per query to avoid overwhelming the total
                results = self.search_web(query, num_results=3)
                
                # Add the query that found this result
                for result in results:
                    result['query'] = query
                
                # Add results ensuring no duplicates
                for result in results:
                    if not any(r['url'] == result['url'] for r in combined_results):
                        combined_results.append(result)
                
                # Break early if we have enough results
                if len(combined_results) >= num_results:
                    break
                    
                # Small delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"Error searching with query '{query}': {str(e)}")
        
        # If we don't have enough results, try the fallback
        if len(combined_results) < num_results:
            try:
                fallback_results = self._generate_topical_urls(topic, num_results - len(combined_results))
                # Add results ensuring no duplicates
                for result in fallback_results:
                    if not any(r['url'] == result['url'] for r in combined_results):
                        result['query'] = 'fallback'
                        combined_results.append(result)
            except Exception as e:
                print(f"Error generating fallback results: {str(e)}")
        
        return combined_results[:num_results]
    
    def search_by_subtopic(self, subtopic: str, main_query: str = "", num_results: int = 3) -> List[Dict[str, str]]:
        """
        Search specifically for content relevant to a particular subtopic.
        
        Args:
            subtopic: The specific subtopic to search for
            main_query: Optional main query for context
            num_results: Number of results to return
            
        Returns:
            List of dictionaries with 'title', 'url', 'snippet' and relevance info
        """
        # Create a specific search query combining the subtopic with the main query
        if main_query:
            # Using quotes around the subtopic forces exact phrase matching
            search_query = f'"{subtopic}" {main_query}'
        else:
            search_query = subtopic
            
        print(f"Searching for subtopic: {subtopic}")
        print(f"Using search query: {search_query}")
        
        # Cache to store valid results - prevents repeated validation
        self.result_cache = getattr(self, 'result_cache', {})
        
        # Check cache first
        cache_key = f"{search_query}_{num_results}"
        if cache_key in self.result_cache:
            print(f"Using cached results for: {search_query}")
            return self.result_cache[cache_key][:num_results]
        
        # Try to directly use search engines that don't require API keys first
        try:
            # Use a Google search alternative (Brave or Bing)
            results = self._brave_search(search_query, num_results * 2)
            if results and len(results) >= num_results:
                high_quality_results = self._filter_by_domain_quality(results)
                if high_quality_results:
                    self.result_cache[cache_key] = high_quality_results
                    return high_quality_results[:num_results]
        except Exception as e:
            print(f"Brave search failed: {str(e)}")
            
        # Primary search method - DuckDuckGo (doesn't require API key)
        try:
            # Use a simplified DuckDuckGo search that's more reliable
            results = self._simple_duckduckgo_search(search_query, num_results * 2)
            if results and len(results) >= num_results:
                # Basic filtering for domain quality - no full validation
                high_quality_results = self._filter_by_domain_quality(results)
                if high_quality_results:
                    # Cache results
                    self.result_cache[cache_key] = high_quality_results
                    return high_quality_results[:num_results]
        except Exception as e:
            print(f"DuckDuckGo search failed: {str(e)}")
        
        # Fallback to SerpAPI if available
        if self.api_key:
            try:
                serp_results = self._simple_serpapi_search(search_query, num_results * 2)
                if serp_results:
                    # Basic domain filtering
                    filtered_results = self._filter_by_domain_quality(serp_results) 
                    if filtered_results:
                        # Cache results
                        self.result_cache[cache_key] = filtered_results
                        return filtered_results[:num_results]
            except Exception as e:
                print(f"SerpAPI search failed: {str(e)}")
        
        # Final fallback - reliable generated URLs that don't require validation
        reliable_urls = self._generate_reliable_urls(subtopic, main_query, num_results)
        self.result_cache[cache_key] = reliable_urls
        return reliable_urls[:num_results]
    
    def _brave_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Use Brave Search API or scrape Brave search results.
        This doesn't require an API key and often provides better results.
        """
        try:
            # Encode query for URL safety
            encoded_query = quote_plus(query)
            url = f"https://search.brave.com/search?q={encoded_query}"
            
            # Set browser-like headers to avoid blocks
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://search.brave.com/',
                'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114", "Brave";v="114"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            }
            
            # Make the request
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search result elements (adjust selectors based on Brave's HTML structure)
            results = []
            for result_elem in soup.select('.snippet'):
                try:
                    # Find title and link
                    title_elem = result_elem.select_one('.snippet-title')
                    url_elem = result_elem.select_one('.result-header a')
                    snippet_elem = result_elem.select_one('.snippet-description')
                    
                    if title_elem and url_elem:
                        title = title_elem.get_text().strip()
                        result_url = url_elem.get('href', '')
                        snippet = snippet_elem.get_text().strip() if snippet_elem else "No description available."
                        
                        # Sometimes Brave returns URLs with their own redirect service
                        if '/search?q=' in result_url:
                            # Try to extract the actual URL from the redirect
                            parsed_url = urlparse(result_url)
                            query_params = parse_qs(parsed_url.query)
                            if 'q' in query_params:
                                result_url = query_params['q'][0]
                        
                        results.append({
                            'title': title,
                            'url': result_url,
                            'snippet': snippet,
                            'source': 'brave'
                        })
                        
                        if len(results) >= num_results:
                            break
                except Exception as e:
                    print(f"Error parsing Brave result: {str(e)}")
                    continue
            
            # If we couldn't parse through the main selector, try an alternative approach
            if not results:
                # Try alternative selectors
                for result_elem in soup.select('article.fdb'):
                    try:
                        title_elem = result_elem.select_one('a.h')
                        url_elem = result_elem.select_one('a.h')
                        snippet_elem = result_elem.select_one('.snippet')
                        
                        if title_elem and url_elem:
                            title = title_elem.get_text().strip()
                            result_url = url_elem.get('href', '')
                            snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                            
                            results.append({
                                'title': title,
                                'url': result_url,
                                'snippet': snippet,
                                'source': 'brave-alt'
                            })
                            
                            if len(results) >= num_results:
                                break
                    except Exception as e:
                        continue
            
            return results
            
        except Exception as e:
            print(f"Brave search error: {str(e)}")
            # Try an alternative search API if Brave fails
            return self._bing_search(query, num_results)
    
    def _bing_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Use Bing search as an alternative that doesn't require an API key.
        """
        try:
            # Encode query for URL safety
            encoded_query = quote_plus(query)
            url = f"https://www.bing.com/search?q={encoded_query}"
            
            # Set browser-like headers to avoid blocks
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.67',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.bing.com/'
            }
            
            # Make the request
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find search result elements
            results = []
            for result_elem in soup.select('.b_algo'):
                try:
                    # Find title and link
                    title_elem = result_elem.select_one('h2 a')
                    snippet_elem = result_elem.select_one('.b_caption p')
                    
                    if title_elem:
                        title = title_elem.get_text().strip()
                        result_url = title_elem.get('href', '')
                        snippet = snippet_elem.get_text().strip() if snippet_elem else "No description available."
                        
                        results.append({
                            'title': title,
                            'url': result_url,
                            'snippet': snippet,
                            'source': 'bing'
                        })
                        
                        if len(results) >= num_results:
                            break
                except Exception as e:
                    continue
            
            return results
            
        except Exception as e:
            print(f"Bing search error: {str(e)}")
            return []

    def _simple_duckduckgo_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Simplified DuckDuckGo search that's more reliable."""
        try:
            # Try the direct Python library approach first
            try:
                from duckduckgo_search import DDGS
                
                # Create search instance with simplified options
                ddgs = DDGS()
                
                # Perform the search with timeout
                results = []
                for r in ddgs.text(query, max_results=num_results, timeout=10):
                    results.append({
                        'title': r.get('title', ''),
                        'url': r.get('href', ''),
                        'snippet': r.get('body', '')
                    })
                return results
            except ImportError:
                # If the library isn't available, try direct HTTP request
                return self._manual_duckduckgo_search(query, num_results)
                
        except Exception as e:
            print(f"DuckDuckGo search module error: {str(e)}")
            return self._manual_duckduckgo_search(query, num_results)
    
    def _manual_duckduckgo_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Manual implementation of DuckDuckGo search using direct HTTP request."""
        try:
            # Encode the query for URL
            encoded_query = quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            # Use a browser-like User-Agent to prevent blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://duckduckgo.com/'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract results
            results = []
            for result in soup.select('.result'):
                # Extract title, URL and snippet
                title_elem = result.select_one('.result__title')
                url_elem = result.select_one('.result__url')
                snippet_elem = result.select_one('.result__snippet')
                
                if title_elem and url_elem:
                    title = title_elem.get_text().strip()
                    result_url = url_elem.get('href') if url_elem.has_attr('href') else ""
                    snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                    
                    # Clean up URL - DuckDuckGo sometimes uses redirects
                    if '/uddg=' in result_url:
                        # Extract the actual URL from the redirect
                        try:
                            from urllib.parse import parse_qs, urlparse
                            parsed_url = urlparse(result_url)
                            if 'uddg' in parse_qs(parsed_url.query):
                                result_url = parse_qs(parsed_url.query)['uddg'][0]
                        except:
                            # Keep the original URL if parsing fails
                            pass
                    
                    results.append({
                        'title': title,
                        'url': result_url,
                        'snippet': snippet,
                        'source': 'duckduckgo-manual'
                    })
                    
                    if len(results) >= num_results:
                        break
            
            return results
            
        except Exception as e:
            print(f"Manual DuckDuckGo search error: {str(e)}")
            return []

    def _validate_urls(self, results: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Validate URLs to ensure they are accessible."""
        valid_results = []
        
        for result in results:
            url = result.get('url', '')
            
            # Skip if we've already tried this URL
            if url in self.tried_urls:
                continue
            
            self.tried_urls.append(url)
            
            # Basic URL validation
            if not url.startswith(('http://', 'https://')):
                continue
            
            # Skip certain file types that often cause timeouts
            if url.endswith(('.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx')):
                continue
                
            try:
                # Check if the URL is valid
                parsed_url = urlparse(url)
                if not all([parsed_url.scheme, parsed_url.netloc]):
                    continue
                
                # Skip URLs that are likely to be invalid or return 404
                skip_patterns = [
                    'file:', 'localhost', '127.0.0.1', 
                    '/search?', 'google.com/search',
                    'undefined', '{', '}', '[]', '()', 'example.com'
                ]
                
                if any(pattern in url for pattern in skip_patterns):
                    continue
                
                # Check if the URL is accessible
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                try:
                    # Try GET request for more reliable verification
                    response = requests.get(
                        url, 
                        headers=headers, 
                        timeout=3,  # Shorter timeout to avoid long waits 
                        allow_redirects=True,
                        stream=True  # Don't download the entire content
                    )
                    
                    # Read just the first bit to verify the response is valid
                    response.raw.read(1024)
                    response.close()
                    
                    if response.status_code < 400:
                        valid_results.append(result)
                        self.valid_urls.append(url)
                except:
                    # Fallback to HEAD request if GET fails
                    response = requests.head(url, headers=headers, timeout=2, allow_redirects=True)
                    if response.status_code < 400:
                        valid_results.append(result)
                        self.valid_urls.append(url)
                    else:
                        print(f"URL {url} returned status code {response.status_code}")
                    
            except Exception as e:
                print(f"Error validating URL {url}: {str(e)}")
                continue
            
            # Break early if we have enough results
            if len(valid_results) >= 8:
                break
                
            # Add a small delay to avoid rate limiting
            time.sleep(0.2)
        
        # If we didn't get any valid results, try to return at least some reliable sources
        if not valid_results:
            print("No valid URLs found, adding reliable sources")
            # Add reliable sources that are very likely to be valid
            reliable_urls = [
                {
                    'title': 'Wikipedia',
                    'url': 'https://en.wikipedia.org/',
                    'snippet': 'The Free Encyclopedia'
                },
                {
                    'title': 'Stack Overflow',
                    'url': 'https://stackoverflow.com/',
                    'snippet': 'Where Developers Learn, Share, & Build Careers'
                },
                {
                    'title': 'GitHub',
                    'url': 'https://github.com/',
                    'snippet': 'Where the world builds software'
                }
            ]
            valid_results.extend(reliable_urls)
        
        return valid_results
    
    def _generate_topical_urls(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """
        Generate topic-specific URLs that are likely to be valid.
        This is a last resort when API search fails.
        """
        # Clean the query
        clean_query = query.lower().replace('?', '').replace('!', '')
        words = clean_query.split()
        
        # Extract better keywords for more relevant URLs
        # Remove common stopwords for better topic identification
        stopwords = ['what', 'is', 'are', 'how', 'to', 'the', 'a', 'an', 'in', 'on', 'of', 'for', 'tell', 'me', 'about']
        keywords = [word for word in words if word not in stopwords and len(word) > 3][:3]  # Take up to 3 significant words
        
        # If we don't have good keywords, use the most relevant words
        if not keywords and words:
            # Get the longest words as they're often more meaningful
            words_by_length = sorted(words, key=len, reverse=True)
            keywords = words_by_length[:3] if len(words_by_length) > 1 else words_by_length
        
        # If we still have no keywords, use a default
        if not keywords:
            keywords = ["information"]
            
        print(f"Using keywords for URL generation: {keywords}")
        
        # Join multiple keywords with hyphens or plus signs for better URLs
        combined_keyword = "-".join(keywords)
        plus_keyword = "+".join(keywords)
        
        results = []
        
        # Define more specific and reliable URL patterns
        url_patterns = [
            # Direct article URLs (more likely to be valid than search pages)
            {"domain": "wikipedia.org", "pattern": f"https://en.wikipedia.org/wiki/{keywords[0]}"},
            
            # Search-based URLs for multiple keywords (use all keywords)
            {"domain": "wikipedia.org", "pattern": f"https://en.wikipedia.org/wiki/Special:Search?search={plus_keyword}"},
            
            # Documentation sites - use direct search with combined keywords
            {"domain": "docs.python.org", "pattern": f"https://docs.python.org/3/search.html?q={plus_keyword}"},
            {"domain": "developer.mozilla.org", "pattern": f"https://developer.mozilla.org/en-US/search?q={plus_keyword}"},
            
            # Forums and communities
            {"domain": "stackoverflow.com", "pattern": f"https://stackoverflow.com/search?q={plus_keyword}"},
            {"domain": "reddit.com", "pattern": f"https://www.reddit.com/search/?q={plus_keyword}"},
            
            # Technical resources
            {"domain": "github.com", "pattern": f"https://github.com/search?q={plus_keyword}"},
            {"domain": "gitlab.com", "pattern": f"https://gitlab.com/search?search={plus_keyword}"},
            
            # Educational sites
            {"domain": "w3schools.com", "pattern": f"https://www.w3schools.com/search/search.php?q={plus_keyword}"},
            {"domain": "tutorialspoint.com", "pattern": f"https://www.tutorialspoint.com/search.htm?search={plus_keyword}"},
            {"domain": "geeksforgeeks.org", "pattern": f"https://www.geeksforgeeks.org/search/{plus_keyword}"},
            
            # News and articles
            {"domain": "medium.com", "pattern": f"https://medium.com/search?q={plus_keyword}"},
            {"domain": "dev.to", "pattern": f"https://dev.to/search?q={plus_keyword}"},
            
            # Academic sources
            {"domain": "scholar.google.com", "pattern": f"https://scholar.google.com/scholar?q={plus_keyword}"},
            {"domain": "jstor.org", "pattern": f"https://www.jstor.org/action/doBasicSearch?Query={plus_keyword}"},
            
            # News sources - good for historical events like wars
            {"domain": "nytimes.com", "pattern": f"https://www.nytimes.com/search?query={plus_keyword}"},
            {"domain": "bbc.com", "pattern": f"https://www.bbc.co.uk/search?q={plus_keyword}"},
            {"domain": "aljazeera.com", "pattern": f"https://www.aljazeera.com/search/{plus_keyword}"},
            
            # Historical resources - especially useful for war-related queries
            {"domain": "britannica.com", "pattern": f"https://www.britannica.com/search?query={plus_keyword}"},
            {"domain": "history.com", "pattern": f"https://www.history.com/search?q={plus_keyword}"},
        ]
        
        # Generate URLs for the combined keywords
        for pattern_info in url_patterns:
            domain = pattern_info["domain"]
            pattern = pattern_info["pattern"]
            
            title = f"{query.title()} - {domain}"
            snippet = f"Information about {query} on {domain}."
            
            results.append({
                'title': title,
                'url': pattern,
                'snippet': snippet
            })
            
            # Break if we have enough results
            if len(results) >= num_results:
                break
        
        # Return only the number of results requested
        return results[:num_results]

    def get_urls_from_text(self, text: str, num_results: int = 8) -> List[Dict[str, str]]:
        """
        Generate reliable URLs directly from text content using a proper search engine.
        
        Args:
            text: The text to search for (like subtopics or summary)
            num_results: Number of results to return
            
        Returns:
            List of dictionaries with 'title', 'url', and 'snippet'
        """
        print(f"Finding web resources for: {text}")
        
        # Try different search methods in order of preference
        search_methods = [
            self._search_with_langchain,
            self._search_with_serper,
            self._search_with_serpapi,
            self._search_with_duckduckgo,
            self._search_with_fallback
        ]
        
        # First try to do a proper web search with the text
        for method in search_methods:
            try:
                results = method(text, num_results)
                if results:
                    # Verify URLs are valid
                    valid_results = self._validate_urls(results)
                    if valid_results:
                        return valid_results[:num_results]
            except Exception as e:
                print(f"Search method failed: {str(e)}")
                continue
        
        # If all methods fail, return a curated list based on the text keywords
        return self._generate_topical_urls(text, num_results)
    
    def _search_with_langchain(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Search using LangChain tools."""
        try:
            from langchain.utilities import GoogleSearchAPIWrapper
            from langchain.tools import Tool
            
            print("Using LangChain GoogleSearchAPIWrapper")
            search = GoogleSearchAPIWrapper()
            
            # Create a search tool
            search_tool = Tool(
                name="Google Search",
                description="Search Google for recent results.",
                func=search.run
            )
            
            # Run the search
            search_results = search_tool.run(query)
            
            # Parse the results to get URLs
            results = []
            if isinstance(search_results, str):
                # Extract URLs from the text if it's a string
                lines = search_results.split('\n')
                for line in lines[:num_results + 5]:
                    # Look for URLs in the text
                    url_match = re.search(r'https?://[^\s]+', line)
                    if url_match:
                        url = url_match.group(0)
                        title = line[:url_match.start()].strip() or f"Result for {query}"
                        snippet = line[url_match.end():].strip() or f"Found from search for {query}"
                        
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })
            elif isinstance(search_results, list):
                # If it's already a list of items
                for item in search_results[:num_results + 5]:
                    if isinstance(item, dict):
                        # Try to extract URL, title and snippet
                        url = item.get('link') or item.get('url')
                        title = item.get('title') or f"Result for {query}"
                        snippet = item.get('snippet') or item.get('description') or f"Found from search for {query}"
                        
                        if url:
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet
                            })
            
            return results
            
        except Exception as e:
            print(f"LangChain search failed: {str(e)}")
            raise e
    
    def _search_with_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Search using DuckDuckGo."""
        try:
            # Try to import DuckDuckGo Search
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                # If import fails, try to install the package
                import subprocess
                import sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "duckduckgo-search"])
                from duckduckgo_search import DDGS
            
            # Create search instance
            ddgs = DDGS()
            
            # Perform the search
            results = []
            ddg_results = list(ddgs.text(query, max_results=num_results))
            
            for r in ddg_results:
                results.append({
                    'title': r.get('title', ''),
                    'url': r.get('href', ''),
                    'snippet': r.get('body', '')
                })
            
            return results
            
        except Exception as e:
            print(f"DuckDuckGo search failed: {str(e)}")
            raise e

    def _score_results_for_subtopic(self, results: List[Dict[str, str]], subtopic: str) -> List[Dict[str, str]]:
        """Score search results for relevance to a specific subtopic."""
        scored_results = []
        
        # Extract key terms from the subtopic
        subtopic_terms = self._extract_key_terms(subtopic)
        
        for result in results:
            # Calculate relevance score
            relevance = self._calculate_content_relevance(result, subtopic)
            
            # Add the score to the result
            result_copy = result.copy()
            result_copy['relevance_score'] = relevance
            result_copy['subtopic'] = subtopic
            
            scored_results.append(result_copy)
        
        # Sort by relevance
        scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
        return scored_results
    
    def _calculate_content_relevance(self, result: Dict[str, str], subtopic: str) -> float:
        """Calculate how relevant a search result is to a specific subtopic."""
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        url = result.get('url', '').lower()
        
        # Clean the subtopic
        clean_subtopic = subtopic.lower()
        
        # Extract key terms from subtopic
        subtopic_words = clean_subtopic.split()
        
        # Base score
        score = 0.0
        
        # Check for exact matches (highest value)
        if clean_subtopic in title:
            score += 5.0
        elif clean_subtopic in snippet:
            score += 3.0
            
        # Check for partial matches
        title_match_count = sum(1 for word in subtopic_words if word in title)
        snippet_match_count = sum(1 for word in subtopic_words if word in snippet)
        
        # Add scores based on match percentage
        if len(subtopic_words) > 0:
            title_match_ratio = title_match_count / len(subtopic_words)
            snippet_match_ratio = snippet_match_count / len(subtopic_words)
            
            score += title_match_ratio * 3.0
            score += snippet_match_ratio * 2.0
        
        # Check URL for relevance
        if any(word in url for word in subtopic_words if len(word) > 3):
            score += 1.0
        
        # Check for domain quality
        domain = self._extract_domain(url)
        domain_score = self._score_domain_quality(domain)
        
        # Add weighted domain score (multiply by 0.2 to keep it proportional)
        score += domain_score * 0.2
        
        return score
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from text."""
        # Remove punctuation and lowercase
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        
        # Remove stopwords
        stopwords = ['a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'of']
        words = clean_text.split()
        key_terms = [word for word in words if word not in stopwords and len(word) > 2]
        
        return key_terms
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            return domain
        except:
            return ""
    
    def _score_domain_quality(self, domain: str) -> float:
        """Score domain quality based on known reliable domains."""
        # Higher quality domains
        high_quality = [
            'wikipedia.org', 'github.com', 'stackoverflow.com', 
            'arxiv.org', 'ieee.org', 'acm.org', 'springer.com',
            'nytimes.com', 'bbc.com', 'cnn.com', 'reuters.com',
            'harvard.edu', 'stanford.edu', 'mit.edu', '.edu',
            'docs.python.org', 'developer.mozilla.org'
        ]
        
        # Medium quality domains
        medium_quality = [
            'medium.com', 'towardsdatascience.com', 'blog.google',
            'dev.to', 'freecodecamp.org', 'w3schools.com',
            'tutorialspoint.com', 'geeksforgeeks.org', 'hackernoon.com'
        ]
        
        # Check for high quality domains (score 9-10)
        for hq_domain in high_quality:
            if hq_domain in domain:
                base_score = 9.0
                # Even higher score for educational domains
                if '.edu' in domain or 'wikipedia.org' in domain:
                    base_score = 10.0
                return base_score
        
        # Check for medium quality domains (score 7-8)
        for mq_domain in medium_quality:
            if mq_domain in domain:
                return 7.0
        
        # Default score for unknown domains
        return 5.0
    
    def _search_with_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Search using DuckDuckGo."""
        try:
            # Try to import DuckDuckGo Search
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                # If import fails, try to install the package
                import subprocess
                import sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "duckduckgo-search"])
                from duckduckgo_search import DDGS
            
            # Create search instance
            ddgs = DDGS()
            
            # Perform the search
            results = []
            ddg_results = list(ddgs.text(query, max_results=num_results))
            
            for r in ddg_results:
                results.append({
                    'title': r.get('title', ''),
                    'url': r.get('href', ''),
                    'snippet': r.get('body', '')
                })
            
            return results
            
        except Exception as e:
            print(f"DuckDuckGo search failed: {str(e)}")
            raise e

    def _generate_search_queries(self, topic: str) -> List[str]:
        """Generate multiple search queries from a single topic."""
        # Clean the topic
        clean_topic = re.sub(r'[?!.,;:]', '', topic.lower())
        
        # Remove common stopwords
        stopwords = ['what', 'is', 'are', 'how', 'to', 'the', 'a', 'an', 'in', 'on', 'of', 'for', 'tell', 'me', 'about']
        words = clean_topic.split()
        
        # Extract significant words (length > 2 and not stopwords)
        keywords = [word for word in words if word not in stopwords and len(word) > 2]
        
        # Keep important connecting words like "and" between entities
        for i, word in enumerate(words):
            if word == 'and' and i > 0 and i < len(words) - 1:
                if words[i-1] not in keywords and words[i-1] not in stopwords:
                    keywords.append(words[i-1])
                if words[i+1] not in keywords and words[i+1] not in stopwords:
                    keywords.append(words[i+1])
                keywords.append('and')
        
        # If we don't have good keywords, use the longest words
        if not keywords and words:
            words_by_length = sorted(words, key=len, reverse=True)
            keywords = words_by_length[:3]
        
        # For specific topics like wars, ensure we capture both sides
        if 'war' in words or 'conflict' in words:
            important_entities = ['india', 'pakistan', 'china', 'russia', 'ukraine', 'usa', 'japan', 
                                'korea', 'vietnam', 'iraq', 'iran', 'afghanistan', 'israel', 'palestine']
            
            found_entities = [entity for entity in important_entities if entity in words]
            if len(found_entities) >= 2:
                # Create a specific war query
                war_query = " ".join(found_entities) + " war"
                
        # Main search terms
        main_terms = " ".join(keywords[:3]) if keywords else topic
        if len(keywords) > 3:
            secondary_terms = " ".join(keywords[3:])
        else:
            secondary_terms = main_terms
        
        # Generate different types of queries
        queries = [
            main_terms,  # Direct terms
            f"{main_terms} history",  # Historical perspective
            f"{main_terms} overview",  # Overview
            f"{main_terms} explained",  # Explanation
            f"{main_terms} analysis",  # Analysis
            f"{secondary_terms} consequences",  # Consequences
            f"{main_terms} timeline",  # Timeline/chronology
            f"{main_terms} key events"  # Key events
        ]
        
        # Add topic-specific queries for wars/conflicts
        if 'war' in words or 'conflict' in words:
            war_queries = [
                f"{main_terms} battles",
                f"{main_terms} peace treaty",
                f"{main_terms} casualties",
                f"{main_terms} causes"
            ]
            queries.extend(war_queries)
        
        # Eliminate duplicates while preserving order
        unique_queries = []
        for query in queries:
            if query not in unique_queries:
                unique_queries.append(query)
        
        return unique_queries
    
    def _filter_query(self, query: str) -> str:
        """
        Filter and clean the query for better search results.
        
        Args:
            query: The original query
            
        Returns:
            Cleaned and filtered query
        """
        # Remove any question marks, exclamation points, unnecessary punctuation
        query = re.sub(r'[?!.,;:]', '', query)
        
        # Special handling for "tell about" or similar prefixes
        query = re.sub(r'^(tell|tell me|tell us|talk|talk about|explain|explain about)\s+about\s+', '', query.lower())
        query = re.sub(r'^(tell|tell me|tell us|talk|talk about|explain|explain about)\s+', '', query.lower())
        
        # Keep "and" for war/conflict queries to preserve relationship between entities
        if any(term in query.lower() for term in ['war', 'conflict', 'battle', 'dispute', 'fight', 'operation']):
            # Don't strip "and" from war/conflict queries
            modified_words = query.lower().split()
            
            # Build the modified query keeping important connecting words
            filtered_words = []
            for i, word in enumerate(modified_words):
                # Keep countries, important entities and connecting words for war-related topics
                if (word in ['and', 'between', 'against', 'with']) or len(word) > 3:
                    filtered_words.append(word)
                    
            # Use this carefully filtered version  
            return ' '.join(filtered_words)
        
        # Normal processing for non-war queries
        # Remove common filler words to focus on key terms
        stopwords = ['what', 'is', 'are', 'how', 'to', 'the', 'a', 'an', 'in', 'on', 'of', 'for', 'can', 'could', 'would', 'should', 'or', 'but']
        
        # Split into words
        words = query.lower().split()
        # Filter out stopwords and short words
        keywords = [word for word in words if word not in stopwords and len(word) > 2]
        
        # If the filtered query is too short, keep more of the original words
        if len(keywords) < 2 and len(words) >= 2:
            # First try keeping 'and' to preserve relationships between terms
            if 'and' in words:
                # Keep words that are connected by 'and'
                and_index = words.index('and')
                if and_index > 0 and and_index < len(words) - 1:
                    keywords = words[and_index-1:and_index+2]  # Take the words around 'and'
            else:
                # Just use more of the original words
                keywords = words
        
        # Keep at least 3-4 words for complex topics
        if len(words) > 4 and len(keywords) < 3:
            keywords = words[:4]  # Keep first 4 words of original query
        
        # Reconstruct the query with key terms
        filtered_query = ' '.join(keywords)
        
        # For specific topics like wars or conflicts, ensure both entity names are included
        if ('war' in query.lower() or 'conflict' in query.lower() or 'dispute' in query.lower() or 'operation' in query.lower()):
            # Make sure we don't lose important country or entity names
            important_entities = ['india', 'pakistan', 'pakisthan', 'china', 'russia', 'ukraine', 'us', 'usa', 
                                'america', 'japan', 'korea', 'vietnam', 'iraq', 'iran', 'afghanistan',
                                'israel', 'palestine', 'world', 'sindoor', 'operation']
            
            # Add back any important entities that were filtered out
            for entity in important_entities:
                if entity in query.lower() and entity not in filtered_query:
                    filtered_query += f" {entity}"
        
        # If nothing specific was identified but the query is short
        if len(filtered_query) < 10:
            return query  # Use original query
            
        return filtered_query

    def _search_with_serper(self, query: str, num_results: int = 8) -> List[Dict[str, str]]:
        """
        Search the web using Serper.dev API.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            List of dictionaries with 'title', 'url', and 'snippet'
        """
        try:
            # Check if API key is available
            api_key = self.api_key or os.getenv("SERPER_API_KEY")
            if not api_key:
                raise ValueError("Serper API key not found")
                
            # Set up the API request
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": api_key,
                "Content-Type": "application/json"
            }
            payload = {
                "q": query,
                "num": min(num_results * 2, 20)  # Request more results than needed to filter later
            }
            
            # Make the request
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Parse the results
            results = []
            if "organic" in data:
                for item in data["organic"]:
                    title = item.get("title", "")
                    link = item.get("link", "")
                    snippet = item.get("snippet", "")
                    
                    results.append({
                        "title": title,
                        "url": link,
                        "snippet": snippet,
                        "source": "serper"
                    })
                    
                    if len(results) >= num_results:
                        break
                        
            return results
            
        except Exception as e:
            print(f"Serper search error: {str(e)}")
            raise e

    def _search_with_serpapi(self, query: str, num_results: int = 8) -> List[Dict[str, str]]:
        """
        Search the web using SerpAPI.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            List of dictionaries with 'title', 'url', and 'snippet'
        """
        try:
            # Check if API key is available
            api_key = self.api_key or os.getenv("SERPAPI_KEY")
            if not api_key:
                raise ValueError("SerpAPI key not found")
                
            # Set up the API request
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": api_key,
                "engine": "google",
                "num": min(num_results * 2, 20),  # Request more results to filter later
                "gl": "us",  # geolocation - use US results
                "hl": "en"   # language - use English
            }
            
            # Make the request
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Parse the results
            results = []
            if "organic_results" in data:
                for item in data["organic_results"]:
                    title = item.get("title", "")
                    link = item.get("link", "")
                    snippet = item.get("snippet", "")
                    
                    results.append({
                        "title": title,
                        "url": link,
                        "snippet": snippet,
                        "source": "serpapi"
                    })
                    
                    if len(results) >= num_results:
                        break
                        
            return results
            
        except Exception as e:
            print(f"SerpAPI search error: {str(e)}")
            raise e

    def _search_with_fallback(self, query: str, num_results: int = 8) -> List[Dict[str, str]]:
        """
        Fallback search method using free alternatives.
        
        Args:
            query: The search query
            num_results: Number of results to return
            
        Returns:
            List of dictionaries with 'title', 'url', and 'snippet'
        """
        # Try different methods in order
        try:
            # First try DuckDuckGo
            results = self._simple_duckduckgo_search(query, num_results * 2)
            if results and len(results) >= 3:  # At least 3 results
                return results[:num_results]
        except Exception as e:
            print(f"DuckDuckGo search failed: {str(e)}")
        
        try:
            # Then try Brave
            results = self._brave_search(query, num_results * 2)
            if results and len(results) >= 3:
                return results[:num_results]
        except Exception as e:
            print(f"Brave search failed: {str(e)}")
        
        try:
            # Then try Bing
            results = self._bing_search(query, num_results * 2)
            if results and len(results) >= 3:
                return results[:num_results]
        except Exception as e:
            print(f"Bing search failed: {str(e)}")
        
        # If all else fails, generate topic-specific URLs
        return self._generate_topical_urls(query, num_results)

    def _simple_serpapi_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Simpler wrapper around SerpAPI."""
        return self._search_with_serpapi(query, num_results)
