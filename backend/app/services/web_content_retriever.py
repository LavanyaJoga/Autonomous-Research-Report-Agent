"""
Web content retriever service that dynamically fetches current web content
from multiple search engines and APIs to ensure fresh, relevant results.
"""

import os
import re
import json
import random
import asyncio
import logging
from typing import List, Dict, Any, Set, Optional, Tuple
import httpx
import requests
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebContentRetriever:
    """Service for retrieving dynamic web content from various sources."""
    
    def __init__(self):
        """Initialize the web content retriever with API keys from environment."""
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Tracking for unique domains
        self.seen_domains = set()
        
    async def get_dynamic_web_sources(self, query: str, min_sources: int = 7) -> List[Dict[str, Any]]:
        """
        Retrieve dynamic web sources for a query from multiple search engines.
        
        Args:
            query: The search query
            min_sources: Minimum number of sources to return
            
        Returns:
            List of web sources with metadata
        """
        logger.info(f"Getting dynamic web sources for: '{query}'")
        self.seen_domains = set()  # Reset tracking
        
        # Create tasks for different search methods to run in parallel
        tasks = []
        
        # Always try Google scraping for fresh results
        tasks.append(self._scrape_google_search(query))
        
        # Try SerpAPI if key available
        if self.serpapi_key:
            tasks.append(self._serpapi_search(query))
        
        # Always try direct DuckDuckGo search
        tasks.append(self._duckduckgo_search(query))
            
        # Run tasks in parallel with asyncio.gather
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and process results
        all_sources = []
        for result in results:
            if isinstance(result, list):
                for source in result:
                    # Extract domain and check if we've seen it before
                    try:
                        url = source.get("url", "")
                        if not url:
                            continue
                        
                        domain = self._extract_base_domain(url)
                        
                        # Skip if we've already seen this domain
                        if domain in self.seen_domains:
                            continue
                        
                        # Add domain to seen domains
                        self.seen_domains.add(domain)
                        
                        # Add source to results
                        all_sources.append(source)
                        
                        # If we have enough sources, stop
                        if len(all_sources) >= min_sources:
                            break
                    except Exception as e:
                        logger.error(f"Error processing source: {e}")
            elif isinstance(result, Exception):
                logger.error(f"Search method error: {result}")
        
        # If we still don't have enough sources, try extra search engines
        if len(all_sources) < min_sources:
            try:
                # Try Bing search as backup
                bing_results = await self._bing_search(query)
                for source in bing_results:
                    domain = self._extract_base_domain(source.get("url", ""))
                    if domain not in self.seen_domains:
                        self.seen_domains.add(domain)
                        all_sources.append(source)
                        
                        if len(all_sources) >= min_sources:
                            break
            except Exception as e:
                logger.error(f"Error with extra search engines: {e}")
        
        # Log results
        logger.info(f"Retrieved {len(all_sources)} dynamic web sources from {len(self.seen_domains)} unique domains")
        
        # Show first few results for debugging
        for i, source in enumerate(all_sources[:3]):
            logger.debug(f"Source {i+1}: {source.get('title')} - {source.get('url')} ({source.get('source_type', 'unknown')})")
        
        return all_sources
    
    async def _scrape_google_search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Scrape Google search results directly.
        This bypasses API limitations and gets truly current results.
        """
        results = []
        try:
            # Encode query for URL
            encoded_query = quote_plus(query)
            
            # Randomize country code for more diverse results
            country_codes = ['com', 'co.uk', 'ca', 'com.au', 'co.in']
            country_code = random.choice(country_codes)
            
            # Randomize user agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
            ]
            
            # Build headers
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Construct URL
            search_url = f"https://www.google.{country_code}/search?q={encoded_query}&num=15"
            
            # Make the request
            async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
                logger.info(f"Scraping Google search: {search_url}")
                response = await client.get(search_url, timeout=15.0)
                
                if response.status_code != 200:
                    logger.warning(f"Google scrape failed with status code: {response.status_code}")
                    return []
                
                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find search result containers
                search_results = soup.select('div.g')
                logger.info(f"Found {len(search_results)} raw Google results")
                
                # Process each result
                for result in search_results:
                    try:
                        # Find title element
                        title_elem = result.select_one('h3')
                        if not title_elem:
                            continue
                        
                        # Extract title
                        title = title_elem.get_text()
                        
                        # Find URL element - might be in different places depending on Google's HTML structure
                        link_elem = result.select_one('a')
                        if not link_elem:
                            continue
                        
                        # Extract URL
                        url = link_elem.get('href', '')
                        
                        # Google prepends URLs with /url?q= - extract the actual URL
                        if url.startswith('/url?q='):
                            url = url.split('/url?q=')[1].split('&')[0]
                        
                        # Skip non-HTTP URLs
                        if not url.startswith('http'):
                            continue
                            
                        # Extract snippet
                        snippet_elem = result.select_one('div.VwiC3b, span.st')
                        snippet = snippet_elem.get_text() if snippet_elem else ""
                        
                        # Add to results
                        results.append({
                            'url': url,
                            'title': title,
                            'snippet': snippet,
                            'source_type': 'google-scrape'
                        })
                    except Exception as e:
                        logger.error(f"Error extracting Google result: {e}")
            
            # Log success
            logger.info(f"Successfully scraped {len(results)} Google results")
            return results[:num_results]
        
        except Exception as e:
            logger.error(f"Google scraping error: {e}")
            return []
    
    async def _serpapi_search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Search using SerpAPI."""
        results = []
        try:
            if not self.serpapi_key:
                logger.warning("No SerpAPI key available")
                return []
            
            # Construct URL with parameters
            params = {
                "q": query,
                "api_key": self.serpapi_key,
                "engine": "google",
                "google_domain": "google.com",
                "gl": "us",
                "hl": "en",
                "num": num_results
            }
            
            # Make the request
            url = "https://serpapi.com/search"
            async with httpx.AsyncClient() as client:
                logger.info(f"Searching via SerpAPI: {query}")
                response = await client.get(url, params=params, timeout=15.0)
                
                if response.status_code != 200:
                    logger.warning(f"SerpAPI request failed with status code: {response.status_code}")
                    return []
                
                # Parse JSON response
                data = response.json()
                
                # Extract organic results
                organic_results = data.get('organic_results', [])
                logger.info(f"Found {len(organic_results)} SerpAPI results")
                
                # Process each result
                for result in organic_results:
                    title = result.get('title', '')
                    link = result.get('link', '')
                    snippet = result.get('snippet', '')
                    
                    if title and link and link.startswith('http'):
                        results.append({
                            'url': link,
                            'title': title,
                            'snippet': snippet,
                            'source_type': 'serpapi'
                        })
            
            return results[:num_results]
        
        except Exception as e:
            logger.error(f"SerpAPI search error: {e}")
            return []
    
    async def _duckduckgo_search(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo."""
        results = []
        try:
            # Encode query
            encoded_query = quote_plus(query)
            
            # Headers
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://duckduckgo.com/',
            }
            
            # Use DuckDuckGo's HTML page
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            # Make the request
            async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
                logger.info(f"Searching via DuckDuckGo: {query}")
                response = await client.get(url, timeout=15.0)
                
                if response.status_code != 200:
                    logger.warning(f"DuckDuckGo request failed with status code: {response.status_code}")
                    return []
                
                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find search result containers
                search_results = soup.select('.result')
                logger.info(f"Found {len(search_results)} DuckDuckGo results")
                
                # Process each result
                for result in search_results:
                    try:
                        # Find title and link
                        title_elem = result.select_one('.result__title a')
                        if not title_elem:
                            continue
                        
                        # Extract title and URL
                        title = title_elem.get_text()
                        url = title_elem.get('href', '')
                        
                        # DuckDuckGo uses redirects - extract the actual URL
                        if '/uddg=' in url:
                            url = url.split('/uddg=')[1].split('&')[0]
                            import urllib.parse
                            url = urllib.parse.unquote(url)
                        
                        # Skip if URL is not valid
                        if not url.startswith('http'):
                            continue
                        
                        # Extract snippet
                        snippet_elem = result.select_one('.result__snippet')
                        snippet = snippet_elem.get_text() if snippet_elem else ""
                        
                        # Add to results
                        results.append({
                            'url': url,
                            'title': title,
                            'snippet': snippet,
                            'source_type': 'duckduckgo'
                        })
                    except Exception as e:
                        logger.error(f"Error extracting DuckDuckGo result: {e}")
            
            # Log success
            logger.info(f"Successfully extracted {len(results)} DuckDuckGo results")
            return results[:num_results]
        
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
    
    async def _bing_search(self, query: str, num_results: int = 8) -> List[Dict[str, Any]]:
        """Search using Bing."""
        results = []
        try:
            # Encode query
            encoded_query = quote_plus(query)
            
            # Headers with common browser user agent
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            # Construct URL
            url = f"https://www.bing.com/search?q={encoded_query}"
            
            # Make the request
            async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
                logger.info(f"Searching via Bing: {query}")
                response = await client.get(url, timeout=15.0)
                
                if response.status_code != 200:
                    logger.warning(f"Bing request failed with status code: {response.status_code}")
                    return []
                
                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find search result containers
                search_results = soup.select('.b_algo')
                logger.info(f"Found {len(search_results)} Bing results")
                
                # Process each result
                for result in search_results:
                    try:
                        # Find title and link
                        title_elem = result.select_one('h2 a')
                        if not title_elem:
                            continue
                        
                        # Extract title and URL
                        title = title_elem.get_text()
                        url = title_elem.get('href', '')
                        
                        # Skip if URL is not valid
                        if not url or not url.startswith('http'):
                            continue
                        
                        # Extract snippet
                        snippet_elem = result.select_one('.b_caption p')
                        snippet = snippet_elem.get_text() if snippet_elem else ""
                        
                        # Add to results
                        results.append({
                            'url': url,
                            'title': title,
                            'snippet': snippet,
                            'source_type': 'bing'
                        })
                    except Exception as e:
                        logger.error(f"Error extracting Bing result: {e}")
            
            # Log success
            logger.info(f"Successfully extracted {len(results)} Bing results")
            return results[:num_results]
        
        except Exception as e:
            logger.error(f"Bing search error: {e}")
            return []
    
    def _extract_base_domain(self, url: str) -> str:
        """Extract the base domain from a URL to avoid duplicates."""
        if not url:
            return ""
        
        try:
            # Parse the URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Remove 'www' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Extract main domain parts
            parts = domain.split('.')
            
            # Handle special cases like co.uk, com.au
            if len(parts) > 2:
                if parts[-2] in ['co', 'com', 'org', 'net', 'edu', 'gov', 'ac'] and len(parts[-1]) <= 3:
                    return '.'.join(parts[-3:])  # Return something like example.co.uk
            
            # Standard case
            if len(parts) > 1:
                return '.'.join(parts[-2:])  # Return something like example.com
            
            return domain
        except:
            return ""
