"""
Dynamic search service that provides real-time web search results without static URLs.
"""

import os
import json
import random
import logging
import traceback
import asyncio
from typing import List, Dict, Any, Optional
import httpx
from urllib.parse import quote_plus, urlparse
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SearchService:
    """Service that provides dynamic web search results from actual search engines."""
    
    @staticmethod
    async def search_query(query: str, min_results: int = 7) -> List[Dict[str, Any]]:
        """
        Search for information about a query using multiple real search engines.
        Returns dynamic, up-to-date results from actual web searches.
        
        Args:
            query: The search query
            min_results: Minimum number of results to return
            
        Returns:
            List of search results with URLs, titles, and snippets
        """
        logger.info(f"Searching for information about: '{query}'")
        
        # Try multiple search methods in parallel to ensure we get enough results
        tasks = [
            SearchService._search_google(query),
            SearchService._search_bing(query),
            SearchService._search_duckduckgo(query),
            SearchService._search_serpapi(query) if os.getenv("SERPAPI_KEY") else None,
        ]
        
        # Remove None tasks (e.g., if SERPAPI_KEY is not available)
        tasks = [t for t in tasks if t is not None]
        
        # Use asyncio.gather to run searches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results, handling any exceptions
        all_results = []
        seen_domains = set()  # Track domains to avoid duplicates
        
        for result in results:
            if isinstance(result, list):
                for item in result:
                    try:
                        # Extract domain to avoid duplicates
                        domain = urlparse(item.get('url', '')).netloc
                        base_domain = SearchService._get_base_domain(domain)
                        
                        # Skip if we've already seen this domain
                        if base_domain in seen_domains:
                            continue
                            
                        seen_domains.add(base_domain)
                        all_results.append(item)
                        
                        # If we have enough results, stop adding more
                        if len(all_results) >= min_results:
                            break
                    except Exception as e:
                        logger.error(f"Error processing search result: {e}")
            elif isinstance(result, Exception):
                logger.error(f"Search method error: {result}")
        
        # If we still don't have enough results, try a fallback method
        if len(all_results) < min_results:
            try:
                fallback_results = await SearchService._fallback_search(query)
                for item in fallback_results:
                    domain = urlparse(item.get('url', '')).netloc
                    base_domain = SearchService._get_base_domain(domain)
                    if base_domain not in seen_domains:
                        seen_domains.add(base_domain)
                        all_results.append(item)
            except Exception as e:
                logger.error(f"Fallback search error: {e}")
                
        # Log the results
        logger.info(f"Found {len(all_results)} dynamic search results from {len(seen_domains)} unique domains")
        
        return all_results
    
    @staticmethod
    async def get_enhanced_search_results(query: str) -> Dict[str, Any]:
        """
        Get enhanced search results with categorized information.
        
        Args:
            query: The search query
            
        Returns:
            Dictionary with categorized search results
        """
        logger.info(f"Getting enhanced search results for: '{query}'")
        
        basic_results = await SearchService.search_query(query, min_results=10)
        
        # Track domains to avoid duplicates
        seen_domains = set()
        
        # Categorize results
        categorized = {
            "academic": [],
            "news": [],
            "reference": [],
            "other": []
        }
        
        for result in basic_results:
            try:
                url = result.get("url", "")
                domain = url.split("//")[-1].split("/")[0]
                base_domain = SearchService._get_base_domain(domain)
                
                # Skip if we've already seen this domain
                if base_domain in seen_domains:
                    continue
                
                seen_domains.add(base_domain)
                
                # Categorize based on domain
                if any(term in domain for term in ["scholar", "research", "science", "edu", "ac.", "jstor", "arxiv"]):
                    categorized["academic"].append(result)
                elif any(term in domain for term in ["news", "nyt", "bbc", "cnn", "reuters", "guardian"]):
                    categorized["news"].append(result)
                elif any(term in domain for term in ["wikipedia", "britannica", "dictionary", "encyclopedia"]):
                    categorized["reference"].append(result)
                else:
                    categorized["other"].append(result)
            except Exception as e:
                logger.error(f"Error categorizing result {result.get('url')}: {e}")
                continue
        
        return {
            "query": query,
            "results": basic_results,
            "categorized": categorized,
            "total_found": len(basic_results)
        }
    
    @staticmethod
    async def _search_google(query: str) -> List[Dict[str, Any]]:
        """Perform a real Google search through scraping."""
        try:
            # Encode query for URL
            encoded_query = quote_plus(query)
            
            # Use random country codes to avoid regional limitations
            country_codes = ['com', 'co.uk', 'ca', 'com.au']
            country_code = random.choice(country_codes)
            
            # Use a diverse set of user agents to avoid blocking
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/91.0.4472.80 Mobile/15E148 Safari/604.1'
            ]
            
            # Build headers to make request look like a browser
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.google.com/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Direct Google scraping approach
            scraper_url = f"https://www.google.{country_code}/search?q={encoded_query}&num=10"
            
            logger.info(f"Performing Google search via direct scraping: {scraper_url}")
            
            # Make the actual HTTP request to Google
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                response = await client.get(scraper_url)
                
                # Check if request was successful
                if response.status_code != 200:
                    logger.warning(f"Google search failed with status {response.status_code}")
                    return []
                
                # Use BeautifulSoup for parsing the HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                results = []
                search_results = soup.select('div.g')
                
                for result in search_results:
                    try:
                        # Find title and URL
                        title_element = result.select_one('h3')
                        link_element = result.select_one('a')
                        snippet_element = result.select_one('div.VwiC3b')
                        
                        if title_element and link_element:
                            title = title_element.get_text()
                            url = link_element.get('href')
                            
                            # Extract actual URL from Google's redirect
                            if url and url.startswith('/url?q='):
                                url = url.split('/url?q=')[1].split('&')[0]
                                
                            # Verify URL is valid
                            if not url or not (url.startswith('http://') or url.startswith('https://')):
                                continue
                                
                            snippet = snippet_element.get_text() if snippet_element else ""
                            
                            # Add to results
                            results.append({
                                'url': url,
                                'title': title,
                                'snippet': snippet,
                                'source': f'google-{country_code}'
                            })
                    except Exception as e:
                        logger.error(f"Error parsing Google result: {e}")
                
                return results
                
        except Exception as e:
            logger.error(f"Google search error: {traceback.format_exc()}")
            return []
    
    @staticmethod
    async def _search_bing(query: str) -> List[Dict[str, Any]]:
        """Perform a real Bing search."""
        results = []
        try:
            # Use Bing Search API if key is available
            subscription_key = os.getenv("BING_SEARCH_V7_SUBSCRIPTION_KEY")
            
            # If API key not available, try web scraping
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            headers = {
                "User-Agent": user_agent,
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            encoded_query = quote_plus(query)
            url = f"https://www.bing.com/search?q={encoded_query}"
            
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url)
                
                # Use BS4 to extract results
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract search results
                for result in soup.select(".b_algo"):
                    title_element = result.select_one("h2 a")
                    if not title_element:
                        continue
                        
                    title = title_element.get_text()
                    link = title_element.get("href")
                    
                    # Get snippet
                    snippet_element = result.select_one(".b_caption p")
                    snippet = snippet_element.get_text() if snippet_element else ""
                    
                    if link and link.startswith(('http://', 'https://')):
                        results.append({
                            "url": link,
                            "title": title,
                            "snippet": snippet,
                            "source": "bing-scraper"
                        })
            
            return results
                    
        except Exception as e:
            logger.error(f"Bing search error: {traceback.format_exc()}")
            return []
    
    @staticmethod
    async def _search_duckduckgo(query: str) -> List[Dict[str, Any]]:
        """Perform a real DuckDuckGo search."""
        results = []
        try:
            # Encode query for URL
            encoded_query = quote_plus(query)
            
            # Use random user agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            ]
            
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            # Use DDG's HTML endpoint
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url)
                
                # Check if request was successful
                if response.status_code != 200:
                    logger.warning(f"DuckDuckGo search failed with status {response.status_code}")
                    return []
                
                # Use BeautifulSoup for parsing the HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find search result containers
                search_results = soup.select('.result')
                
                for result in search_results:
                    try:
                        # Find title and URL
                        title_element = result.select_one('.result__title a')
                        if not title_element:
                            continue
                            
                        title = title_element.get_text()
                        url = title_element.get('href')
                        
                        # DDG uses internal redirects, extract the real URL
                        if url and '/uddg=' in url:
                            import urllib.parse
                            url = urllib.parse.unquote(url.split('/uddg=')[1].split('&')[0])
                        
                        # Skip non-http links
                        if not url or not (url.startswith('http://') or url.startswith('https://')):
                            continue
                            
                        # Find snippet
                        snippet_element = result.select_one('.result__snippet')
                        snippet = snippet_element.get_text() if snippet_element else ""
                        
                        # Add to results
                        results.append({
                            'url': url,
                            'title': title,
                            'snippet': snippet,
                            'source': 'duckduckgo'
                        })
                    except Exception as e:
                        logger.error(f"Error parsing DuckDuckGo result: {e}")
                        continue
                
                return results
                
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {traceback.format_exc()}")
            return []
    
    @staticmethod
    async def _search_serpapi(query: str) -> List[Dict[str, Any]]:
        """Perform a search using SerpAPI if API key is available."""
        results = []
        try:
            serpapi_key = os.getenv("SERPAPI_KEY")
            if not serpapi_key:
                return []
                
            # Encode query for URL
            encoded_query = quote_plus(query)
            
            # Build URL with parameters
            url = f"https://serpapi.com/search?q={encoded_query}&api_key={serpapi_key}&engine=google"
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                
                # Check if request was successful
                if response.status_code != 200:
                    logger.warning(f"SerpAPI search failed with status {response.status_code}")
                    return []
                
                # Parse JSON response
                data = response.json()
                
                # Extract organic results
                organic_results = data.get('organic_results', [])
                
                for result in organic_results:
                    results.append({
                        'url': result.get('link'),
                        'title': result.get('title'),
                        'snippet': result.get('snippet', ''),
                        'source': 'serpapi'
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"SerpAPI search error: {traceback.format_exc()}")
            return []
    
    @staticmethod
    async def _fallback_search(query: str) -> List[Dict[str, Any]]:
        """Last-resort fallback search using httpbin to test connectivity."""
        try:
            # Just to see if we can make HTTP requests
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("https://httpbin.org/get")
                
                if response.status_code == 200:
                    logger.info("Httpbin connectivity test successful, but all search methods failed")
                else:
                    logger.warning(f"Httpbin connectivity test failed with status {response.status_code}")
            
            # We can't do a real search, so we need to generate search-like results
            # based on the query but make it clear they're generated
            
            # Extract keywords from query
            keywords = query.lower().split()
            keywords = [k for k in keywords if len(k) > 3]
            if not keywords:
                keywords = query.lower().split()
            
            # Generate search-like results
            main_keyword = keywords[0] if keywords else "topic"
            
            # Here we're returning empty results instead of fake ones
            return []
            
        except Exception as e:
            logger.error(f"Fallback search error: {e}")
            return []
    
    @staticmethod
    def _get_base_domain(domain: str) -> str:
        """Extract base domain from full domain name."""
        parts = domain.split('.')
        
        # Handle special cases like co.uk
        if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net', 'edu', 'gov', 'ac']:
            return '.'.join(parts[-3:])
            
        # Standard case
        if len(parts) >= 2:
            return '.'.join(parts[-2:])
            
        return domain
