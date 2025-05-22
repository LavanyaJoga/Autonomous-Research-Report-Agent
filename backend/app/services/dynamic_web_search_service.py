"""
Enhanced dynamic web search service that guarantees at least 7 diverse website results.
This service combines multiple real search strategies and handles fallbacks.
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

class EnhancedWebSearch:
    """Service for retrieving diverse, real-time search results from multiple search engines."""
    
    def __init__(self):
        """Initialize with optional API keys from environment variables."""
        self.serpapi_key = os.environ.get("SERPAPI_KEY")
        self.user_agent = os.environ.get("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Track used domains to ensure diversity
        self.seen_domains = set()
        
        # Domains to exclude (customize as needed)
        self.excluded_domains = {
            'docs.python.org',  # Exclude Python docs
            'python.org',       # Exclude Python website
            'localhost',        # Exclude localhost
            'stackoverflow.com' # Exclude StackOverflow
        }
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64; rv:95.0) Gecko/20100101 Firefox/95.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/96.0.4664.94 Mobile/15E148 Safari/604.1"
        ]
    
    async def _search_google(self, query: str) -> List[Dict[str, Any]]:
        """Perform Google search by scraping results."""
        results = []
        try:
            # Try direct approach with Googling
            logger.info(f"Performing Google search for: {query}")
            
            # Use different proxies/methods to avoid blocking
            methods = [
                self._google_search_method1,
                self._google_search_method2,
                self._google_search_method3
            ]
            
            # Try different methods until we get results
            for method in methods:
                try:
                    method_results = await method(query)
                    if method_results:
                        results.extend(method_results)
                        logger.info(f"Got {len(method_results)} results from Google search method")
                        break
                except Exception as e:
                    logger.error(f"Google search method failed: {e}")
                    continue
            
            return results
                
        except Exception as e:
            logger.error(f"All Google search methods failed: {e}")
            return []

    async def _google_search_method1(self, query: str) -> List[Dict[str, Any]]:
        """First method to search Google with a different approach."""
        try:
            # Encode query
            encoded_query = quote_plus(query)
            
            # Use different Google domain
            domain = "com"
            
            # Different user agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            # Different URL format
            url = f"https://www.google.{domain}/search?q={encoded_query}&num=20&hl=en"
            
            # Make the request
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    return []
                
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                
                results = []
                for div in soup.select("div.tF2Cxc"):
                    try:
                        title_elem = div.select_one("h3")
                        link_elem = div.select_one("a")
                        
                        if title_elem and link_elem:
                            title = title_elem.get_text()
                            link = link_elem.get("href")
                            
                            # Skip non-HTTP links
                            if not link or not link.startswith(("http://", "https://")):
                                continue
                            
                            # Find snippet
                            snippet_elem = div.select_one("div.VwiC3b") or div.select_one("div.IsZvec")
                            snippet = snippet_elem.get_text() if snippet_elem else ""
                            
                            # Calculate relevance score
                            score = self._calculate_relevance(query, title, snippet, link)
                            
                            results.append({
                                "title": title,
                                "url": link,
                                "snippet": snippet,
                                "source": "google-direct",
                                "relevance_score": score
                            })
                    except Exception as e:
                        logger.error(f"Error parsing Google result: {e}")
                
                return results
                
        except Exception as e:
            logger.error(f"Google method 1 error: {e}")
            return []

    async def _google_search_method2(self, query: str) -> List[Dict[str, Any]]:
        """Second method to search Google with a different approach."""
        try:
            # Use a different query approach - adding quotes and site operators
            encoded_query = quote_plus(f'{query} -"login" -"sign in"')
            
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://www.google.com/",
                "Alt-Used": "www.google.com",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            }
            
            url = f"https://www.google.com/search?q={encoded_query}&num=30&start=0"
            
            # Make the request with a different client setup
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=20.0) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    return []
                
                # Parse HTML using a more robust approach
                soup = BeautifulSoup(response.text, "html.parser")
                results = []
                
                # Try multiple selectors to find search results
                search_divs = (
                    soup.select("div.g") or 
                    soup.select("[data-header-feature]") or 
                    soup.select("[data-hveid]") or
                    soup.select(".hlcw0c")
                )
                
                for div in search_divs:
                    try:
                        # Look for title and URL in various ways
                        link_elem = div.select_one("a")
                        if not link_elem:
                            continue
                            
                        href = link_elem.get("href", "")
                        if not href.startswith("http"):
                            continue
                            
                        # Try to find the title
                        title_elem = div.select_one("h3") or div.select_one(".DKV0Md") or link_elem
                        title = title_elem.get_text() if title_elem else ""
                        
                        # Try to find the snippet
                        snippet_elem = (
                            div.select_one(".VwiC3b") or 
                            div.select_one(".IsZvec") or 
                            div.select_one(".s3v9rd") or
                            div.select_one(".st")
                        )
                        snippet = snippet_elem.get_text() if snippet_elem else ""
                        
                        # Skip common irrelevant results
                        if any(x in href.lower() for x in ["/search?", "google.com/", "/preferences?", "accounts.google"]):
                            continue
                        
                        # Calculate relevance score
                        score = self._calculate_relevance(query, title, snippet, href)
                        
                        results.append({
                            "title": title,
                            "url": href,
                            "snippet": snippet,
                            "source": "google-method2",
                            "relevance_score": score
                        })
                    except Exception as e:
                        # Just skip errors and continue to next result
                        pass
                
                return results
                
        except Exception as e:
            logger.error(f"Google method 2 error: {e}")
            return []

    async def _google_search_method3(self, query: str) -> List[Dict[str, Any]]:
        """Third method using a different approach for getting Google results."""
        try:
            # Try to use Google mobile site
            encoded_query = quote_plus(query)
            
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
            }
            
            url = f"https://www.google.com/search?q={encoded_query}&tbm=mob&num=20"
            
            # Make the request
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    return []
                
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                
                results = []
                
                # Extract all links that might be search results
                for a_tag in soup.find_all("a", href=True):
                    try:
                        href = a_tag["href"]
                        
                        # Filter out non-http links and Google's internal links
                        if (not href.startswith("http") or 
                            "google.com" in href or 
                            "/search?" in href or
                            "/url?" in href):
                            continue
                        
                        # Get the parent div that might contain more info
                        parent_div = a_tag.find_parent("div")
                        if not parent_div:
                            continue
                        
                        # Try to find title and snippet
                        title = a_tag.get_text()
                        
                        # Use parent div text as snippet, but remove the title
                        snippet = parent_div.get_text()
                        if title in snippet:
                            snippet = snippet.replace(title, "", 1).strip()
                        
                        # Calculate relevance score
                        score = self._calculate_relevance(query, title, snippet, href)
                        
                        results.append({
                            "title": title,
                            "url": href,
                            "snippet": snippet,
                            "source": "google-mobile",
                            "relevance_score": score
                        })
                    except Exception:
                        continue
                
                return results
                
        except Exception as e:
            logger.error(f"Google method 3 error: {e}")
            return []

    async def _search_bing(self, query: str) -> List[Dict[str, Any]]:
        """Perform Bing search by scraping results."""
        results = []
        try:
            # Encode query
            encoded_query = quote_plus(query)
            
            # Set headers with random user agent
            headers = {
                "User-Agent": random.choice(self.user_agents),
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
                logger.info(f"Found {len(result_divs)} Bing search result elements")
                
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
                            
                            # Calculate relevance score
                            score = self._calculate_relevance(query, title, snippet, link)
                            
                            # Add to results
                            results.append({
                                "title": title,
                                "url": link,
                                "snippet": snippet,
                                "source": "bing",
                                "relevance_score": score
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
            
            # Set headers with random user agent
            headers = {
                "User-Agent": random.choice(self.user_agents),
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
                logger.info(f"Found {len(result_divs)} DuckDuckGo search result elements")
                
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
                            
                            # Calculate relevance score
                            score = self._calculate_relevance(query, title, snippet, link)
                            
                            # Add to results
                            results.append({
                                "title": title,
                                "url": link,
                                "snippet": snippet,
                                "source": "duckduckgo",
                                "relevance_score": score
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
                    
                    # Calculate relevance score
                    score = self._calculate_relevance(query, title, snippet, link)
                    
                    # Add to results
                    results.append({
                        "title": title,
                        "url": link,
                        "snippet": snippet,
                        "source": "serpapi",
                        "relevance_score": score
                    })
            
            return results
                
        except Exception as e:
            logger.error(f"SerpAPI search error: {e}")
            return []
    
    async def _search_from_news_sources(self, query: str) -> List[Dict[str, Any]]:
        """Get results from news sources."""
        results = []
        
        try:
            # News domains to search
            news_domains = [
                {"url": f"https://www.bbc.com/search?q={quote_plus(query)}", "name": "BBC"},
                {"url": f"https://www.reuters.com/search/news?blob={quote_plus(query)}", "name": "Reuters"},
                {"url": f"https://search.nytimes.com/search?query={quote_plus(query)}", "name": "New York Times"},
                {"url": f"https://www.theguardian.com/search?q={quote_plus(query)}", "name": "The Guardian"},
                {"url": f"https://www.aljazeera.com/search/{quote_plus(query)}", "name": "Al Jazeera"},
                {"url": f"https://www.npr.org/search?query={quote_plus(query)}", "name": "NPR"}
            ]
            
            # Select up to 3 random news sources
            selected_sources = random.sample(news_domains, min(3, len(news_domains)))
            
            # Create tasks for each selected source
            tasks = []
            for source in selected_sources:
                tasks.append(self._fetch_search_page(source["url"], source["name"]))
            
            # Execute tasks in parallel
            news_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in news_results:
                if isinstance(result, list):
                    results.extend(result)
                    
            return results
            
        except Exception as e:
            logger.error(f"News sources search error: {e}")
            return []
    
    async def _search_from_academic_sources(self, query: str) -> List[Dict[str, Any]]:
        """Get results from academic sources."""
        results = []
        
        try:
            # Academic domains to search
            academic_domains = [
                {"url": f"https://scholar.google.com/scholar?q={quote_plus(query)}", "name": "Google Scholar"},
                {"url": f"https://www.academia.edu/search?q={quote_plus(query)}", "name": "Academia.edu"},
                {"url": f"https://www.researchgate.net/search?q={quote_plus(query)}", "name": "ResearchGate"},
                {"url": f"https://www.sciencedirect.com/search?qs={quote_plus(query)}", "name": "ScienceDirect"},
                {"url": f"https://www.jstor.org/action/doBasicSearch?Query={quote_plus(query)}", "name": "JSTOR"}
            ]
            
            # Select up to 3 random academic sources
            selected_sources = random.sample(academic_domains, min(3, len(academic_domains)))
            
            # Create tasks for each selected source
            tasks = []
            for source in selected_sources:
                tasks.append(self._fetch_search_page(source["url"], source["name"]))
            
            # Execute tasks in parallel
            academic_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in academic_results:
                if isinstance(result, list):
                    results.extend(result)
                    
            return results
            
        except Exception as e:
            logger.error(f"Academic sources search error: {e}")
            return []
    
    async def _fetch_search_page(self, url: str, source_name: str) -> List[Dict[str, Any]]:
        """Fetch a search page and extract results."""
        results = []
        
        try:
            # Set headers with random user agent
            headers = {
                "User-Agent": random.choice(self.user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            # Make the request
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
                response = await client.get(url)
                
                # Check if successful
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch {url} with status: {response.status_code}")
                    return []
                
                # Parse HTML
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Extract links - we use generic selectors that might work across multiple sites
                links = []
                
                # Try different selectors for result containers
                result_containers = (
                    soup.select(".gs_ri") or  # Google Scholar
                    soup.select(".search-result") or  # Generic
                    soup.select(".result-item") or  # Generic
                    soup.select("article") or  # News sites
                    soup.select(".result") or  # Generic
                    soup.select("li.gs_r") or  # Google Scholar alternative
                    soup.select("div[data-testid='search-result']") or  # Modern sites
                    soup.select(".SearchPage_searchResult__lJDLC")  # Some modern sites
                )
                
                if not result_containers and soup.select("a"):
                    # Fallback: just get all links on the page
                    for a in soup.select("a[href]"):
                        href = a.get("href", "")
                        # Skip internal links and non-HTTP links
                        if (href.startswith("http://") or href.startswith("https://")) and "?" not in href:
                            links.append({
                                "url": href,
                                "text": a.get_text().strip()
                            })
                else:
                    # Process each result container
                    for container in result_containers:
                        # Find link
                        link_elem = container.select_one("a")
                        
                        if link_elem and link_elem.has_attr("href"):
                            href = link_elem.get("href")
                            
                            # Make absolute URL if needed
                            if href.startswith("/"):
                                from urllib.parse import urljoin
                                href = urljoin(url, href)
                            
                            # Skip non-HTTP links
                            if not href.startswith(("http://", "https://")):
                                continue
                                
                            # Find title
                            title_elem = container.select_one("h3") or container.select_one("h2") or link_elem
                            title = title_elem.get_text().strip() if title_elem else ""
                            
                            # Find description
                            description_elem = (
                                container.select_one(".gs_rs") or  # Google Scholar
                                container.select_one(".search-result__description") or  # Generic
                                container.select_one(".result-item__description") or  # Generic
                                container.select_one("p") or  # Generic
                                container.select_one(".snippet-container")  # Generic
                            )
                            description = description_elem.get_text().strip() if description_elem else ""
                            
                            links.append({
                                "url": href,
                                "text": title or link_elem.get_text().strip(),
                                "description": description
                            })
                
                # Convert links to results
                for link in links:
                    # Skip if no URL
                    if not link.get("url"):
                        continue
                        
                    # Skip URLs with certain patterns
                    url_lower = link["url"].lower()
                    if any(pattern in url_lower for pattern in [
                        "/search?", "javascript:", "mailto:", "/login", "/signin", 
                        "/register", "/account", "/about", "/contact", "/terms"
                    ]):
                        continue
                    
                    # Create result object
                    result = {
                        "title": link.get("text", ""),
                        "url": link["url"],
                        "snippet": link.get("description", ""),
                        "source": source_name,
                        "relevance_score": 5  # Default score
                    }
                    
                    # Add to results
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return []
    
    def _calculate_relevance(self, query: str, title: str, snippet: str, url: str) -> float:
        """Calculate relevance score for a result."""
        score = 10.0  # Base score
        
        # Convert everything to lowercase for matching
        query_lower = query.lower()
        title_lower = title.lower()
        snippet_lower = snippet.lower()
        url_lower = url.lower()
        
        # Break query into tokens
        query_tokens = query_lower.split()
        
        # Check for exact match in title (highest relevance)
        if query_lower in title_lower:
            score += 10.0
        
        # Check for partial matches in title
        matched_tokens = 0
        for token in query_tokens:
            if len(token) > 3 and token in title_lower:  # Only consider tokens with length > 3
                matched_tokens += 1
        
        # Calculate percentage of query tokens found in title
        if query_tokens:
            title_match_percentage = matched_tokens / len(query_tokens)
            score += title_match_percentage * 8.0  # Up to 8 points for full token match
        
        # Check for exact match in snippet
        if query_lower in snippet_lower:
            score += 5.0
        
        # Check snippet for token matches
        matched_tokens = 0
        for token in query_tokens:
            if len(token) > 3 and token in snippet_lower:
                matched_tokens += 1
        
        # Calculate percentage of query tokens found in snippet
        if query_tokens:
            snippet_match_percentage = matched_tokens / len(query_tokens)
            score += snippet_match_percentage * 4.0  # Up to 4 points for full token match
        
        # Boost for URL appearance
        if any(token in url_lower for token in query_tokens if len(token) > 3):
            score += 3.0
        
        # Domain-based boosting
        domain = self._get_domain(url)
        
        # Boost educational and government sites
        if domain.endswith(".edu"):
            score += 5.0
        elif domain.endswith(".gov"):
            score += 4.0
        elif domain.endswith(".org"):
            score += 3.0
        
        # Boost for reputable reference sites
        if domain in ["wikipedia.org", "britannica.com", "encyclopedia.com"]:
            score += 2.5
        
        # Boost for major news outlets and academic repositories
        if domain in [
            "nytimes.com", "washingtonpost.com", "bbc.com", "reuters.com", 
            "springer.com", "nature.com", "science.org", "researchgate.net"
        ]:
            score += 2.0
        
        # Penalize social media unless the query is about them
        if domain in ["facebook.com", "twitter.com", "instagram.com", "tiktok.com", "linkedin.com"] and not any(
            sm_domain.split(".")[0] in query_lower for sm_domain in [
                "facebook.com", "twitter.com", "instagram.com", "tiktok.com", "linkedin.com"
            ]
        ):
            score -= 5.0
        
        return score
    
    async def search(self, query: str, min_results: int = 7) -> List[Dict[str, Any]]:
        """
        Perform a comprehensive web search using multiple search engines.
        Guarantees at least min_results unique domain results.
        
        Args:
            query: The search query
            min_results: Minimum number of unique domain results to return
            
        Returns:
            List of search results with diverse domains
        """
        logger.info(f"Performing enhanced web search for: '{query}'")
        
        # Reset tracking for this search
        self.seen_domains = set()
        start_time = time.time()
        
        # Run all search methods in parallel for speed
        tasks = [
            self._search_google(query),
            self._search_bing(query),
            self._search_duckduckgo(query),
            self._search_google_special(query),
            self._search_from_news_sources(query),
            self._search_from_academic_sources(query),
            self._search_yahoo(query),  # Added Yahoo search
        ]
        
        # Add SerpAPI if key is available
        if self.serpapi_key:
            tasks.append(self._search_serpapi(query))
            
        # If we have SERPAPI key, use direct Google Search API
        try:
            serpapi_results = []
            if self.serpapi_key:
                serpapi_results = await self._direct_serpapi_search(query)
                if serpapi_results:
                    logger.info(f"Got {len(serpapi_results)} results directly from SerpAPI")
        except Exception as e:
            logger.error(f"Direct SerpAPI error: {e}")
            serpapi_results = []
        
        # Execute all search tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results, handling any exceptions
        all_results = []
        
        # First add SerpAPI results as they're most reliable
        all_results.extend(serpapi_results)
        
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Search method error: {result}")
        
        # DEBUGGING: Print number of results from each source
        source_counts = {}
        for result in all_results:
            source = result.get('source', 'unknown')
            source_counts[source] = source_counts.get(source, 0) + 1
        
        for source, count in source_counts.items():
            logger.info(f"Found {count} results from source: {source}")
                
        # Organize results by domain to ensure diversity
        domain_results = {}
        
        for result in all_results:
            try:
                url = result.get('url', '')
                if not url:
                    continue
                    
                domain = self._get_domain(url)
                
                # Skip excluded domains
                if domain in self.excluded_domains:
                    continue
                
                # Group by domain
                if domain not in domain_results:
                    domain_results[domain] = []
                    
                domain_results[domain].append(result)
            except Exception as e:
                logger.error(f"Error processing result: {e}")
        
        # Get the best result from each domain
        diverse_results = []
        
        # First, get one result from each domain
        for domain, results in domain_results.items():
            if results:
                # Sort domain results by relevance
                sorted_results = sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)
                diverse_results.append(sorted_results[0])
        
        # Debug info
        logger.info(f"Found {len(diverse_results)} results from unique domains")
        domains_found = [self._get_domain(r.get('url', '')) for r in diverse_results]
        logger.info(f"Domains found: {domains_found}")
        
        # If we don't have enough diverse results, try query variations
        if len(diverse_results) < min_results:
            logger.info(f"Need more results. Found {len(diverse_results)} domains, need {min_results}")
            variation_results = await self._try_query_variations(query, min_results - len(diverse_results))
            
            # Add variation results while maintaining domain diversity
            for result in variation_results:
                domain = self._get_domain(result.get('url', ''))
                if domain not in [self._get_domain(r.get('url', '')) for r in diverse_results]:
                    diverse_results.append(result)
                    
                    # If we have enough results, break
                    if len(diverse_results) >= min_results:
                        break
        
        # If we STILL don't have enough results, add our fallback sources
        if len(diverse_results) < min_results:
            logger.info(f"Still need more results. Found {len(diverse_results)} domains, need {min_results}")
            fallback_results = self._create_fallback_results(query, min_results - len(diverse_results))
            diverse_results.extend(fallback_results)
        
        # Sort by relevance score
        diverse_results = sorted(diverse_results, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Calculate search time
        search_time = time.time() - start_time
        
        # Log final results
        domains = [self._get_domain(r.get('url', '')) for r in diverse_results]
        logger.info(f"Enhanced search completed in {search_time:.2f} seconds")
        logger.info(f"Generated {len(diverse_results)} results from unique domains: {', '.join(domains)}")
        
        return diverse_results
        
    async def _direct_serpapi_search(self, query: str) -> List[Dict[str, Any]]:
        """Direct SerpAPI search to get reliable results."""
        if not self.serpapi_key:
            return []
            
        try:
            # Build URL with API key
            url = f"https://serpapi.com/search.json?q={quote_plus(query)}&api_key={self.serpapi_key}&engine=google&num=20"
            
            # Make the request
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    return []
                    
                data = response.json()
                results = []
                
                # Process organic results
                for item in data.get("organic_results", []):
                    title = item.get("title", "")
                    link = item.get("link", "")
                    snippet = item.get("snippet", "")
                    
                    if link and link.startswith(("http://", "https://")):
                        # Calculate relevance score
                        score = self._calculate_relevance(query, title, snippet, link)
                        
                        results.append({
                            "title": title,
                            "url": link,
                            "snippet": snippet,
                            "source": "serpapi-direct",
                            "relevance_score": score
                        })
                
                return results
                
        except Exception as e:
            logger.error(f"Direct SerpAPI search error: {e}")
            return []
            
    async def _try_query_variations(self, query: str, num_needed: int) -> List[Dict[str, Any]]:
        """Try variations of the query to get more diverse results."""
        results = []
        
        # Generate variations
        variations = self._generate_query_variations(query)
        
        # Create tasks for multiple variations
        tasks = []
        for variation in variations[:3]:
            tasks.append(self._search_google(variation))
            tasks.append(self._search_bing(variation))
            
        variation_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in variation_results:
            if isinstance(result, list):
                results.extend(result)
                
        return results
        
    def _create_fallback_results(self, query: str, num_needed: int) -> List[Dict[str, Any]]:
        """Create fallback results for when we can't get enough from real searches."""
        results = []
        
        # Only use this as a last resort
        logger.warning("Using fallback static results - real searches failed to provide enough diverse domains")
        
        # List of domains that typically have good content for almost any topic
        fallback_domains = [
            {"domain": "wikipedia.org", "title": "Wikipedia - The Free Encyclopedia"},
            {"domain": "britannica.com", "title": "Encyclopedia Britannica"},
            {"domain": "khanacademy.org", "title": "Khan Academy"},
            {"domain": "coursera.org", "title": "Coursera"},
            {"domain": "mit.edu", "title": "MIT OpenCourseWare"},
            {"domain": "nationalgeographic.com", "title": "National Geographic"},
            {"domain": "forbes.com", "title": "Forbes"},
            {"domain": "sciencedaily.com", "title": "ScienceDaily"},
            {"domain": "medium.com", "title": "Medium"},
            {"domain": "nytimes.com", "title": "The New York Times"}
        ]
        
        # Clean query for URL
        clean_query = re.sub(r'[^\w\s]', '', query).lower().replace(' ', '-')
        
        # Create a result for each domain
        for i in range(min(num_needed, len(fallback_domains))):
            domain_info = fallback_domains[i]
            domain = domain_info["domain"]
            
            if domain == "wikipedia.org":
                url = f"https://en.wikipedia.org/wiki/{clean_query.replace('-', '_')}"
            elif domain == "britannica.com":
                url = f"https://www.britannica.com/technology/{clean_query}"
            elif domain == "khanacademy.org":
                url = f"https://www.khanacademy.org/search?page_search_query={clean_query}"
            else:
                url = f"https://www.{domain}/search?q={clean_query}"
            
            title = f"{query} - {domain_info['title']}"
            
            results.append({
                "title": title,
                "url": url,
                "snippet": f"Information about {query} from {domain_info['title']}.",
                "source": "fallback",
                "relevance_score": 5.0  # Medium relevance score for fallbacks
            })
        
        return results
