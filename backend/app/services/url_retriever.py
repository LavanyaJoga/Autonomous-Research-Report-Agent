"""
URL retrieval service that combines multiple search strategies to ensure comprehensive results.
"""

import os
import json
import random
import logging
import asyncio
from typing import List, Dict, Any, Set
import requests
from urllib.parse import urlparse, quote_plus
import httpx

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class URLRetriever:
    """Specialized service to retrieve diverse and relevant URLs for research queries."""
    
    # Search APIs we can use
    SEARCH_APIS = {
        "serper": "https://serpapi.com/search",
        "bing": "https://api.bing.microsoft.com/v7.0/search",
        "ddg": "https://api.duckduckgo.com/",
    }
    
    @staticmethod
    async def get_diverse_urls(query: str, min_urls: int = 7) -> List[Dict[str, Any]]:
        """
        Get a diverse set of relevant URLs for the given query.
        
        Args:
            query: The search query
            min_urls: Minimum number of URLs to return
            
        Returns:
            List of URL objects with metadata
        """
        logger.info(f"Getting diverse URLs for query: '{query}'")
        
        # Try multiple strategies in parallel
        tasks = [
            URLRetriever._get_urls_from_search_engines(query),
            URLRetriever._get_urls_from_academic_sources(query),
            URLRetriever._get_urls_from_specialized_sources(query),
            URLRetriever._get_urls_from_news_sources(query)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results, removing duplicates
        all_urls = []
        seen_domains = set()
        
        # Process successful results
        for result in results:
            if isinstance(result, list):
                for url_data in result:
                    try:
                        domain = urlparse(url_data.get("url", "")).netloc
                        base_domain = URLRetriever._get_base_domain(domain)
                        
                        # Check if we've already seen this domain
                        if base_domain in seen_domains:
                            continue
                            
                        seen_domains.add(base_domain)
                        all_urls.append(url_data)
                    except Exception as e:
                        logger.error(f"Error processing URL: {e}")
        
        # If we still don't have enough URLs, try additional strategies
        if len(all_urls) < min_urls:
            logger.info(f"Only found {len(all_urls)} URLs, trying additional strategies")
            
            # Try direct HTTP requests to common domains with the query
            try:
                additional_urls = await URLRetriever._get_urls_from_direct_requests(query)
                for url_data in additional_urls:
                    domain = urlparse(url_data.get("url", "")).netloc
                    base_domain = URLRetriever._get_base_domain(domain)
                    
                    if base_domain not in seen_domains:
                        seen_domains.add(base_domain)
                        all_urls.append(url_data)
            except Exception as e:
                logger.error(f"Error with direct requests: {e}")
        
        # Sort by relevance score
        all_urls.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Ensure we return at most min_urls results
        return all_urls[:min_urls]
    
    @staticmethod
    async def _get_urls_from_search_engines(query: str) -> List[Dict[str, Any]]:
        """Get URLs from general search engines using actual search requests."""
        urls = []
        
        try:
            # Use Google Search via custom search function
            google_results = await URLRetriever._search_google(query)
            if google_results:
                urls.extend(google_results)
                logger.info(f"Added {len(google_results)} results from Google search")
            
            # If we didn't get enough results, try Bing
            if len(urls) < 5:
                bing_results = await URLRetriever._search_bing(query)
                if bing_results:
                    urls.extend(bing_results)
                    logger.info(f"Added {len(bing_results)} results from Bing search")
            
            # If we still need more, try DuckDuckGo
            if len(urls) < 5:
                ddg_results = await URLRetriever._search_duckduckgo(query)
                if ddg_results:
                    urls.extend(ddg_results)
                    logger.info(f"Added {len(ddg_results)} results from DuckDuckGo search")
            
            return urls
        except Exception as e:
            logger.error(f"Error in search engines retrieval: {e}")
            # Don't return static fallbacks if real searches fail
            return []
    
    @staticmethod
    async def _search_google(query: str, num_results: int = 8) -> List[Dict[str, Any]]:
        """
        Perform a real Google search using a custom scraper approach.
        This returns actual current web results without using static URLs.
        """
        results = []
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
                'Cache-Control': 'max-age=0',
            }
            
            # Try searching with SerpAPI if key is available
            serpapi_key = os.getenv("SERPAPI_KEY")
            if serpapi_key:
                logger.info("Using SerpAPI for Google search")
                try:
                    params = {
                        'q': query,
                        'api_key': serpapi_key,
                        'engine': 'google',
                        'num': 10,
                        'gl': 'us',
                    }
                    # Use httpx for async request
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        response = await client.get('https://serpapi.com/search', params=params)
                        if response.status_code == 200:
                            data = response.json()
                            organic_results = data.get('organic_results', [])
                            
                            for result in organic_results:
                                url = result.get('link')
                                title = result.get('title', '')
                                snippet = result.get('snippet', '')
                                
                                # Calculate relevance score
                                score = URLRetriever._calculate_relevance_score(url, title, snippet, query)
                                
                                results.append({
                                    'url': url,
                                    'title': title,
                                    'snippet': snippet,
                                    'source': 'google-serpapi',
                                    'relevance_score': score
                                })
                            
                            return results[:num_results]
                except Exception as e:
                    logger.error(f"SerpAPI failed, falling back to direct scraping: {e}")
            
            # Direct Google scraping approach as fallback
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
                
                # Find search result containers - the exact selectors may need updating
                # as Google frequently changes their HTML structure
                search_results = soup.select('div.g')
                
                for result in search_results:
                    try:
                        # Find title and URL
                        title_element = result.select_one('h3')
                        if not title_element:
                            continue
                            
                        title = title_element.get_text()
                        
                        # Find the link - Google often uses data-ved attributes
                        link_element = result.select_one('a')
                        if not link_element:
                            continue
                            
                        url = link_element.get('href')
                        
                        # Google prepends URLs with /url?q= - extract the actual URL
                        if url and url.startswith('/url?q='):
                            url = url.split('/url?q=')[1].split('&')[0]
                            
                        # Skip non-http links or Javascript links
                        if not url or not (url.startswith('http://') or url.startswith('https://')):
                            continue
                            
                        # Find snippet - this varies by Google version, try multiple approaches
                        snippet_element = result.select_one('div.VwiC3b, span.st, div[data-content-feature="1"]')
                        snippet = snippet_element.get_text() if snippet_element else ""
                        
                        # Calculate relevance score
                        score = URLRetriever._calculate_relevance_score(url, title, snippet, query)
                        
                        results.append({
                            'url': url,
                            'title': title,
                            'snippet': snippet,
                            'source': f'google-{country_code}',
                            'relevance_score': score
                        })
                        
                        if len(results) >= num_results:
                            break
                    except Exception as e:
                        logger.error(f"Error parsing search result: {e}")
                        continue
        except Exception as e:
            logger.error(f"Google search error: {e}")
            
        return results
    
    @staticmethod
    async def _search_bing(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Perform a real Bing search."""
        results = []
        try:
            # Use Bing Search API if key is available
            subscription_key = os.getenv("BING_SEARCH_V7_SUBSCRIPTION_KEY")
            
            if subscription_key:
                # Use the Bing Search API
                endpoint = "https://api.bing.microsoft.com/v7.0/search"
                headers = {"Ocp-Apim-Subscription-Key": subscription_key}
                params = {"q": query, "count": num_results, "textDecorations": True, "textFormat": "HTML"}
                
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(endpoint, headers=headers, params=params)
                    data = response.json()
                    
                    for item in data.get("webPages", {}).get("value", []):
                        url = item.get("url")
                        title = item.get("name")
                        snippet = item.get("snippet")
                        
                        # Calculate relevance score
                        score = URLRetriever._calculate_relevance_score(url, title, snippet, query)
                        
                        results.append({
                            "url": url,
                            "title": title,
                            "snippet": snippet,
                            "source": "bing-api",
                            "relevance_score": score
                        })
            else:
                # Fallback to Bing web scraping
                user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
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
                        
                        # Calculate relevance score
                        score = URLRetriever._calculate_relevance_score(link, title, snippet, query)
                        
                        results.append({
                            "url": link,
                            "title": title,
                            "snippet": snippet,
                            "source": "bing-scraper",
                            "relevance_score": score
                        })
                        
                        if len(results) >= num_results:
                            break
        except Exception as e:
            logger.error(f"Bing search error: {e}")
            
        return results
    
    @staticmethod
    async def _search_duckduckgo(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
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
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://duckduckgo.com/',
                'Connection': 'keep-alive',
            }
            
            # Use DDG's API-like endpoint
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
                            url = url.split('/uddg=')[1].split('&')[0]
                        
                        # URL decode
                        import urllib.parse
                        url = urllib.parse.unquote(url)
                            
                        # Find snippet
                        snippet_element = result.select_one('.result__snippet')
                        snippet = snippet_element.get_text() if snippet_element else ""
                        
                        # Calculate relevance score
                        score = URLRetriever._calculate_relevance_score(url, title, snippet, query)
                        
                        results.append({
                            'url': url,
                            'title': title,
                            'snippet': snippet,
                            'source': 'duckduckgo',
                            'relevance_score': score
                        })
                        
                        if len(results) >= num_results:
                            break
                    except Exception as e:
                        logger.error(f"Error parsing DuckDuckGo result: {e}")
                        continue
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            
        return results
    
    @staticmethod
    async def _get_urls_from_academic_sources(query: str) -> List[Dict[str, Any]]:
        """Get URLs from academic sources."""
        urls = []
        
        # Domains that typically have good academic content
        academic_domains = [
            "scholar.google.com",
            "researchgate.net",
            "academia.edu",
            "sciencedirect.com",
            "jstor.org",
            "nature.com",
            "science.org",
            "pnas.org",  # Proceedings of the National Academy of Sciences
            "arxiv.org", # Pre-prints
            "ncbi.nlm.nih.gov" # National Center for Biotechnology Information
        ]
        
        # Generate academic URLs based on the query
        for domain in academic_domains[:5]:  # Limit to 5 sources
            if domain == "scholar.google.com":
                url = f"https://{domain}/scholar?q={quote_plus(query)}"
                title = f"Google Scholar - {query}"
            elif domain == "arxiv.org":
                url = f"https://{domain}/search/?query={quote_plus(query)}&searchtype=all"
                title = f"arXiv.org - {query} research papers"
            else:
                url = f"https://{domain}/search?term={quote_plus(query)}"
                title = f"{domain.split('.')[0].capitalize()} - {query}"
            
            snippet = f"Academic research papers and publications about {query} from leading researchers."
            score = URLRetriever._calculate_relevance_score(url, title, snippet, query)
            
            urls.append({
                "url": url,
                "title": title,
                "snippet": snippet,
                "source": "academic",
                "relevance_score": score
            })
        
        return urls
    
    @staticmethod
    async def _get_urls_from_specialized_sources(query: str) -> List[Dict[str, Any]]:
        """Get URLs from specialized knowledge sources."""
        urls = []
        
        specialized_sources = [
            # Encyclopedia sources
            {
                "domain": "en.wikipedia.org",
                "path": f"/wiki/{query.replace(' ', '_')}",
                "title": f"{query} - Wikipedia"
            },
            {
                "domain": "www.britannica.com",
                "path": f"/science/{query.replace(' ', '-').lower()}",
                "title": f"{query} - Encyclopedia Britannica"
            },
            # Government sources
            {
                "domain": "www.cdc.gov",
                "path": f"/topics/{query.replace(' ', '-').lower()}/index.html",
                "title": f"{query} - Centers for Disease Control and Prevention"
            },
            {
                "domain": "www.nih.gov",
                "path": f"/research-training/medical-research-initiatives/{query.replace(' ', '-').lower()}",
                "title": f"{query} - National Institutes of Health"
            },
            # Educational institutes
            {
                "domain": "ocw.mit.edu",
                "path": f"/courses/{query.replace(' ', '-').lower()}",
                "title": f"{query} - MIT OpenCourseWare"
            }
        ]
        
        for source in specialized_sources:
            url = f"https://{source['domain']}{source['path']}"
            title = source["title"]
            snippet = f"Specialized information about {query} from {source['domain'].split('.')[-2]}"
            
            score = URLRetriever._calculate_relevance_score(url, title, snippet, query)
            
            urls.append({
                "url": url,
                "title": title,
                "snippet": snippet,
                "source": "specialized",
                "relevance_score": score
            })
        
        return urls
    
    @staticmethod
    async def _get_urls_from_news_sources(query: str) -> List[Dict[str, Any]]:
        """Get URLs from news and current events sources."""
        urls = []
        
        news_sources = [
            # Science news
            {
                "domain": "www.scientificamerican.com",
                "path": f"/search/?q={quote_plus(query)}",
                "title": f"{query} - Scientific American Articles"
            },
            {
                "domain": "www.sciencenews.org",
                "path": f"/topic/{query.replace(' ', '-').lower()}",
                "title": f"{query} - Science News"
            },
            # General news with science sections
            {
                "domain": "www.nytimes.com",
                "path": f"/search?query={quote_plus(query)}",
                "title": f"{query} - New York Times"
            },
            {
                "domain": "www.theguardian.com",
                "path": f"/science/{query.replace(' ', '-').lower()}",
                "title": f"{query} - The Guardian"
            }
        ]
        
        for source in news_sources:
            url = f"https://{source['domain']}{source['path']}"
            title = source["title"]
            snippet = f"Recent news and developments about {query}"
            
            score = URLRetriever._calculate_relevance_score(url, title, snippet, query)
            
            urls.append({
                "url": url,
                "title": title,
                "snippet": snippet,
                "source": "news",
                "relevance_score": score
            })
        
        return urls
    
    @staticmethod
    async def _get_urls_from_direct_requests(query: str) -> List[Dict[str, Any]]:
        """Get URLs by directly constructing probable URLs."""
        urls = []
        
        # Construct direct URLs that are likely to exist
        direct_urls = [
            f"https://www.khanacademy.org/search?page_search_query={quote_plus(query)}",
            f"https://www.coursera.org/search?query={quote_plus(query)}",
            f"https://www.ted.com/search?q={quote_plus(query)}"
        ]
        
        for url in direct_urls:
            domain = urlparse(url).netloc
            title = f"{query} - {domain.split('.')[-2].capitalize()}"
            snippet = f"Educational resources about {query}"
            
            score = URLRetriever._calculate_relevance_score(url, title, snippet, query)
            
            urls.append({
                "url": url,
                "title": title,
                "snippet": snippet,
                "source": "direct",
                "relevance_score": score
            })
        
        return urls
    
    @staticmethod
    def _calculate_relevance_score(url: str, title: str, snippet: str, query: str) -> int:
        """Calculate relevance score for a URL based on the query."""
        score = 0
        query_terms = [term.lower() for term in query.split() if len(term) > 2]
        
        # Domain quality scoring
        domain = urlparse(url).netloc.lower()
        if any(ext in domain for ext in [".edu", ".gov"]):
            score += 20
        elif ".org" in domain:
            score += 15
        elif any(term in domain for term in ["science", "research", "academic", "journal"]):
            score += 10
        
        # Title relevance
        title = title.lower()
        for term in query_terms:
            if term in title:
                score += 5
                
        # Exact phrase matches in title are best
        if query.lower() in title:
            score += 15
        
        # Snippet relevance
        snippet = snippet.lower()
        for term in query_terms:
            if term in snippet:
                score += 3
        
        # URL path relevance
        path = urlparse(url).path.lower()
        for term in query_terms:
            if term in path:
                score += 4
        
        return score
    
    @staticmethod
    def _get_base_domain(domain: str) -> str:
        """Extract base domain to avoid duplicates from subdomains."""
        parts = domain.split('.')
        
        # Handle cases like co.uk
        if len(parts) > 2 and len(parts[-2]) <= 3 and len(parts[-1]) <= 3:
            return '.'.join(parts[-3:])
        
        # Regular case
        if len(parts) >= 2:
            return '.'.join(parts[-2:])
            
        return domain
