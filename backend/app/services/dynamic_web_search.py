"""
Dynamic web search service that fetches real-time search results from multiple search engines.
Ensures diverse, relevant results from at least 7 different domains - just like Google search.
"""

import os
import re
import json
import time
import random
import asyncio
import logging
import traceback
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urlparse, quote_plus, unquote
import httpx
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamicWebSearch:
    """Service for retrieving diverse, real-time search results from multiple search engines."""
    
    def __init__(self):
        """Initialize with optional API keys from environment variables."""
        self.serpapi_key = os.environ.get("SERPAPI_KEY")
        self.user_agent = os.environ.get("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Track used domains to ensure diversity
        self.seen_domains = set()
        
        # List of domains to avoid (can customize this)
        self.excluded_domains = {
            'docs.python.org',  # Exclude Python docs
        }
        
    async def search(self, query: str, min_results: int = 7) -> List[Dict[str, Any]]:
        """
        Perform a comprehensive web search using multiple search engines and methods.
        
        Args:
            query: The search query
            min_results: Minimum number of unique domain results to return
            
        Returns:
            List of search results with diverse domains
        """
        logger.info(f"Performing dynamic web search for: '{query}'")
        
        # Reset tracking for this search
        self.seen_domains = set()
        start_time = time.time()
        
        # Collect all results from multiple sources
        all_results = []
        
        # First try real Google scraping (most reliable method)
        google_results = await self._search_google(query)
        all_results.extend(self._filter_and_track_domains(google_results))
        
        # If we don't have enough results, try Bing
        if len(all_results) < min_results:
            bing_results = await self._search_bing(query)
            all_results.extend(self._filter_and_track_domains(bing_results))
        
        # If we still don't have enough, try DuckDuckGo
        if len(all_results) < min_results:
            ddg_results = await self._search_duckduckgo(query)
            all_results.extend(self._filter_and_track_domains(ddg_results))
        
        # If SerpAPI key available, use it as well
        if self.serpapi_key and len(all_results) < min_results:
            serpapi_results = await self._search_serpapi(query)
            all_results.extend(self._filter_and_track_domains(serpapi_results))
        
        # If we still don't have enough results, get more creative
        if len(all_results) < min_results:
            # Try specialized searches
            variations = self._generate_query_variations(query)
            special_results = []
            
            # Run these in parallel for speed
            tasks = []
            for variation in variations[:3]:  # Limit to 3 variations
                tasks.append(self._search_google(variation))
            
            variation_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process successful results
            for result in variation_results:
                if isinstance(result, list):
                    special_results.extend(result)
                    
            all_results.extend(self._filter_and_track_domains(special_results))
        
        # Calculate search time
        search_time = time.time() - start_time
        logger.info(f"Dynamic search completed in {search_time:.2f} seconds with {len(all_results)} unique domain results")
        
        # Prioritize and diversify results
        final_results = self._prioritize_results(all_results)
        
        # Log the domains we found
        domains = [self._get_domain(r["url"]) for r in final_results]
        logger.info(f"Found {len(domains)} unique domains: {', '.join(domains[:10])}")
        
        return final_results[:min_results+3]  # Return a few extra to ensure we have enough
    
    def _filter_and_track_domains(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter results to ensure domain diversity and track seen domains.
        """
        filtered_results = []
        
        for result in results:
            url = result.get("url", "")
            if not url:
                continue
                
            # Extract domain
            domain = self._get_domain(url)
            
            # Skip if domain is in exclusion list or already seen
            if domain in self.excluded_domains or domain in self.seen_domains:
                continue
                
            # Add to tracking
            self.seen_domains.add(domain)
            filtered_results.append(result)
        
        return filtered_results
    
    def _get_domain(self, url: str) -> str:
        """Extract the base domain from a URL."""
        try:
            parsed = urlparse(url)
            hostname = parsed.netloc.lower()
            
            # Remove www. prefix
            if hostname.startswith('www.'):
                hostname = hostname[4:]
                
            # Handle special cases (e.g., co.uk, com.au)
            parts = hostname.split('.')
            if len(parts) > 2:
                if parts[-2] in ['co', 'com', 'org', 'net', 'edu', 'gov', 'ac'] and len(parts[-1]) <= 3:
                    return '.'.join(parts[-3:])
                else:
                    return '.'.join(parts[-2:])
            
            return hostname
        except Exception as e:
            logger.error(f"Error extracting domain from {url}: {e}")
            return url
    
    def _prioritize_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize results based on relevance and domain quality."""
        # Score each result
        for result in results:
            score = result.get("relevance", 5)
            
            # Boost for high-quality domains
            domain = self._get_domain(result.get("url", ""))
            
            # Prefer educational and government sites
            if domain.endswith('.edu') or domain.endswith('.gov'):
                score += 10
            elif domain.endswith('.org'):
                score += 5
                
            # Prefer well-known reference sites
            if domain in ['wikipedia.org', 'britannica.com', 'nationalgeographic.com']:
                score += 5
                
            # Avoid social media unless that's the topic
            if domain in ['facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com']:
                score -= 5
                
            result["relevance"] = score
        
        # Sort by relevance
        results.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        
        # Ensure domain diversity in top results
        top_domains = set()
        diverse_results = []
        
        for result in results:
            domain = self._get_domain(result.get("url", ""))
            
            # Always include top results regardless of domain
            if len(diverse_results) < 3:
                diverse_results.append(result)
                top_domains.add(domain)
            # For others, ensure domain diversity
            elif domain not in top_domains:
                diverse_results.append(result)
                top_domains.add(domain)
        
        return diverse_results
    
    def _generate_query_variations(self, query: str) -> List[str]:
        """Generate variations of the query to get more diverse results."""
        variations = []
        
        # Remove question words
        clean_query = re.sub(r'^(what|how|why|when|where|who|which)\s+(is|are|were|was|do|does|did|can|could|would|should)\s+', '', query.lower())
        clean_query = re.sub(r'\?', '', clean_query)
        
        # Add specific variations
        variations.append(f"{clean_query} tutorial")
        variations.append(f"{clean_query} guide")
        variations.append(f"{clean_query} explanation")
        variations.append(f"{clean_query} research")
        variations.append(f"latest on {clean_query}")
        
        # Add the original query
        variations.append(query)
        
        return variations
    
    async def _search_google(self, query: str) -> List[Dict[str, Any]]:
        """Perform Google search by scraping results."""
        results = []
        try:
            # Encode query
            encoded_query = quote_plus(query)
            
            # Use different Google domains to avoid blocking
            domains = ["com", "co.uk", "ca", "com.au"]
            domain = random.choice(domains)
            
            # Rotate user agents
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
                "Mozilla/5.0 (X11; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0"
            ]
            
            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            # Build Google search URL with parameters to get more results
            url = f"https://www.google.{domain}/search?q={encoded_query}&num=30&hl=en&gl=us"
            
            # Make the request
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url)
                
                # Check if successful
                if response.status_code != 200:
                    logger.warning(f"Google search failed with status: {response.status_code}")
                    return []
                
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Find all search result divs - Google keeps changing its HTML structure,
                # so we need to try multiple selectors
                result_divs = soup.select("div.g")
                if not result_divs:
                    # Try alternative selectors
                    result_divs = soup.select("div.yuRUbf, div.MjjYud")
                
                logger.info(f"Found {len(result_divs)} Google search result divs")
                
                # Process each result
                for div in result_divs:
                    try:
                        # Find title and link
                        title_elem = div.select_one("h3")
                        link_elem = div.select_one("a")
                        
                        if title_elem and link_elem:
                            title = title_elem.get_text()
                            link = link_elem.get("href")
                            
                            # Skip non-HTTP links and Google's internal URLs
                            if not link or not link.startswith(("http://", "https://")):
                                continue
                            
                            # Find snippet
                            snippet_elem = div.select_one("div.VwiC3b, span.aCOpRe")
                            snippet = snippet_elem.get_text() if snippet_elem else ""
                            
                            # Add to results
                            results.append({
                                "title": title,
                                "url": link,
                                "snippet": snippet,
                                "source": "google",
                                "relevance": 10  # Base relevance score
                            })
                    except Exception as e:
                        logger.error(f"Error parsing Google result: {e}")
            
            return results
                
        except Exception as e:
            logger.error(f"Google search error: {e}")
            traceback.print_exc()
            return []
    
    async def _search_bing(self, query: str) -> List[Dict[str, Any]]:
        """Perform Bing search by scraping results."""
        results = []
        try:
            # Encode query
            encoded_query = quote_plus(query)
            
            # Set headers
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            # Build URL
            url = f"https://www.bing.com/search?q={encoded_query}&count=30"
            
            # Make the request
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url)
                
                # Check if successful
                if response.status_code != 200:
                    logger.warning(f"Bing search failed with status: {response.status_code}")
                    return []
                
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Find search results
                result_divs = soup.select("li.b_algo")
                logger.info(f"Found {len(result_divs)} Bing search result divs")
                
                # Process each result
                for div in result_divs:
                    try:
                        # Find title and link
                        link_elem = div.select_one("h2 a")
                        
                        if link_elem:
                            title = link_elem.get_text()
                            link = link_elem.get("href")
                            
                            # Skip non-HTTP links
                            if not link or not link.startswith(("http://", "https://")):
                                continue
                            
                            # Find snippet
                            snippet_elem = div.select_one(".b_caption p")
                            snippet = snippet_elem.get_text() if snippet_elem else ""
                            
                            # Add to results
                            results.append({
                                "title": title,
                                "url": link,
                                "snippet": snippet,
                                "source": "bing",
                                "relevance": 8  # Base relevance score
                            })
                    except Exception as e:
                        logger.error(f"Error parsing Bing result: {e}")
            
            return results
                
        except Exception as e:
            logger.error(f"Bing search error: {e}")
            return []
    
    async def _search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """Perform DuckDuckGo search by scraping results."""
        results = []
        try:
            # Encode query
            encoded_query = quote_plus(query)
            
            # Set headers
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            # Build URL for HTML version of DuckDuckGo
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            # Make the request
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url)
                
                # Check if successful
                if response.status_code != 200:
                    logger.warning(f"DuckDuckGo search failed with status: {response.status_code}")
                    return []
                
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Find search results
                result_divs = soup.select(".result")
                logger.info(f"Found {len(result_divs)} DuckDuckGo search result divs")
                
                # Process each result
                for div in result_divs:
                    try:
                        # Find title and link
                        link_elem = div.select_one(".result__a")
                        
                        if link_elem:
                            title = link_elem.get_text()
                            link = link_elem.get("href")
                            
                            # DuckDuckGo uses redirects
                            if link and '/uddg=' in link:
                                link = link.split('/uddg=')[1].split('&')[0]
                                link = unquote(link)
                            
                            # Skip non-HTTP links
                            if not link or not link.startswith(("http://", "https://")):
                                continue
                            
                            # Find snippet
                            snippet_elem = div.select_one(".result__snippet")
                            snippet = snippet_elem.get_text() if snippet_elem else ""
                            
                            # Add to results
                            results.append({
                                "title": title,
                                "url": link,
                                "snippet": snippet,
                                "source": "duckduckgo",
                                "relevance": 7  # Base relevance score
                            })
                    except Exception as e:
                        logger.error(f"Error parsing DuckDuckGo result: {e}")
            
            return results
                
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
    
    async def _search_serpapi(self, query: str) -> List[Dict[str, Any]]:
        """Perform search using SerpAPI."""
        results = []
        
        if not self.serpapi_key:
            return []
            
        try:
            # Prepare parameters
            params = {
                "q": query,
                "api_key": self.serpapi_key,
                "engine": "google",
                "num": 20,
                "gl": "us",
                "hl": "en"
            }
            
            # Make the request
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get("https://serpapi.com/search", params=params)
                
                # Check if successful
                if response.status_code != 200:
                    logger.warning(f"SerpAPI search failed with status: {response.status_code}")
                    return []
                
                # Parse JSON
                data = response.json()
                
                # Extract organic results
                organic_results = data.get("organic_results", [])
                
                # Process each result
                for result in organic_results:
                    title = result.get("title", "")
                    link = result.get("link", "")
                    snippet = result.get("snippet", "")
                    
                    # Skip non-HTTP links
                    if not link or not link.startswith(("http://", "https://")):
                        continue
                    
                    # Add to results
                    results.append({
                        "title": title,
                        "url": link,
                        "snippet": snippet,
                        "source": "serpapi",
                        "relevance": 9  # Base relevance score
                    })
            
            return results
                
        except Exception as e:
            logger.error(f"SerpAPI search error: {e}")
            return []
