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
        
        # Use real search engine APIs instead of static patterns
        try:
            # Try Google search through a scraper (no API key required)
            google_results = self._google_scrape_search(clean_query, 5)
            if google_results:
                results.extend(google_results)
                print(f"Added {len(google_results)} results from Google scraping")
        except Exception as e:
            print(f"Google scrape search failed: {str(e)}")
        
        # If we don't have enough results, try Bing
        if len(results) < num_results:
            try:
                bing_results = self._bing_search(clean_query, num_results - len(results))
                if bing_results:
                    results.extend(bing_results)
                    print(f"Added {len(bing_results)} results from Bing")
            except Exception as e:
                print(f"Bing search failed: {str(e)}")
        
        # If we still don't have enough, try DuckDuckGo
        if len(results) < num_results:
            try:
                ddg_results = self._simple_duckduckgo_search(clean_query, num_results - len(results))
                if ddg_results:
                    results.extend(ddg_results)
                    print(f"Added {len(ddg_results)} results from DuckDuckGo")
            except Exception as e:
                print(f"DuckDuckGo search failed: {str(e)}")
        
        # If we still don't have enough, add some carefully selected dynamic sources
        if len(results) < num_results:
            # Use domain-specific search URLs that are likely to work
            domain_search_patterns = [
                # Academic sources
                {"domain": "scholar.google.com", "pattern": f"https://scholar.google.com/scholar?q={plus_keyword}"},
                
                # Documentation and reliable sources
                {"domain": "wikipedia.org", "pattern": f"https://en.wikipedia.org/wiki/Special:Search?search={plus_keyword}"},
                {"domain": "britannica.com", "pattern": f"https://www.britannica.com/search?query={plus_keyword}"},
                
                # News sources with reliable search functionality
                {"domain": "nytimes.com", "pattern": f"https://www.nytimes.com/search?query={plus_keyword}"},
                {"domain": "bbc.com", "pattern": f"https://www.bbc.co.uk/search?q={plus_keyword}"},
                
                # Technical resources
                {"domain": "github.com", "pattern": f"https://github.com/search?q={plus_keyword}"},
                {"domain": "stackoverflow.com", "pattern": f"https://stackoverflow.com/search?q={plus_keyword}"},
            ]
            
            # Add dynamic sources
            for pattern_info in domain_search_patterns:
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
    
    def _google_scrape_search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Scrape Google search results without using an API.
        This method is more dynamic but may be less reliable than API-based methods.
        """
        try:
            # Encode the query for URL
            encoded_query = quote_plus(query)
            
            # Randomize user agent to avoid being blocked
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
            ]
            
            # Try different country codes to get diverse results
            country_codes = ['com', 'co.uk', 'ca', 'com.au', 'co.in']
            
            results = []
            
            # Try a few different Google domains
            for i, cc in enumerate(country_codes):
                if len(results) >= num_results:
                    break
                    
                # Only try 2 country codes maximum to avoid excessive requests
                if i >= 2:
                    break
                
                try:
                    url = f"https://www.google.{cc}/search?q={encoded_query}&num=10"
                    
                    headers = {
                        'User-Agent': random.choice(user_agents),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Referer': 'https://www.google.com/',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    # Check if we got a valid response
                    if response.status_code == 200:
                        # Parse the HTML response
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Extract search results - look for the main search result divs
                        for result_div in soup.find_all('div', class_=['g', 'tF2Cxc']):
                            try:
                                # Extract title and link
                                title_elem = result_div.find('h3')
                                if not title_elem:
                                    continue
                                    
                                title = title_elem.get_text()
                                
                                # Extract URL - it's typically in an <a> tag within the h3's parent
                                link_elem = title_elem.find_parent('a')
                                if not link_elem:
                                    # Try to find the link elsewhere
                                    link_elem = result_div.find('a')
                                
                                if not link_elem:
                                    continue
                                    
                                link = link_elem.get('href', '')
                                
                                # Google search results often have internal links
                                if link.startswith('/url?q='):
                                    # Extract the actual URL from Google's redirect
                                    link = link.split('/url?q=')[1].split('&')[0]
                                
                                # Find the snippet text
                                snippet_elem = result_div.find('div', class_=['VwiC3b', 'yXK7lf', 'MUxGbd', 'yDYNvb', 'lyLwlc'])
                                snippet = snippet_elem.get_text() if snippet_elem else ""
                                
                                # Add to results if we have a valid URL
                                if link.startswith('http'):
                                    results.append({
                                        'title': title,
                                        'url': link,
                                        'snippet': snippet,
                                        'source': f'google-{cc}'
                                    })
                                    
                                    if len(results) >= num_results:
                                        break
                            except Exception as e:
                                # Skip this result if there's an error
                                continue
                except Exception as e:
                    print(f"Error with Google {cc}: {str(e)}")
                    continue
                    
                # Add a delay between requests to different domains
                time.sleep(1)
            
            return results
            
        except Exception as e:
            print(f"Google scrape search error: {str(e)}")
            return []

# ...existing code...
