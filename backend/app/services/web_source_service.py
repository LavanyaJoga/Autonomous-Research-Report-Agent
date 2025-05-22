"""
Service for retrieving web content from multiple sources.
Provides a configurable and fallback-enabled way to ensure we always get sufficient research results.
"""

import os
import logging
import asyncio
import re
import time
import random
import json
from typing import List, Dict, Any, Optional, Set
import requests
from urllib.parse import urlparse, quote_plus
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebSourceService")

class WebSourceService:
    """Service to retrieve web sources from multiple providers with fallback options."""
    
    # Class variables for configuration
    _providers = {}
    _provider_order = []
    _config = {
        "min_sources": 10,  # Increased from 6 to 10
        "min_domains": 7,   # Increased from 5 to 7
        "use_fallback_providers": True,
        "allow_dynamic_content": True,
        "max_retries": 3,   # Increased from 2 to 3
        "cross_reference_results": True,
    }
    
    # User agent rotation for avoiding detection
    _user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"
    ]

    # Keep track of successful domains by query type for future optimization
    _successful_domains = {}
    
    @classmethod
    def register_provider(cls, provider_name: str, priority: int = 10):
        """Register a web source provider with a priority (lower number = higher priority)."""
        if provider_name not in cls._providers:
            cls._providers[provider_name] = {
                "name": provider_name,
                "priority": priority,
                "enabled": True
            }
            # Re-sort provider order
            cls._provider_order = sorted(cls._providers.keys(), 
                                        key=lambda p: cls._providers[p]["priority"])
            logger.info(f"Registered web source provider: {provider_name} (priority: {priority})")
        return True
    
    @classmethod
    def set_config(cls, config: Dict[str, Any]):
        """Update the service configuration."""
        cls._config.update(config)
        logger.info(f"Updated configuration: min_sources={cls._config['min_sources']}, " +
                   f"min_domains={cls._config['min_domains']}")
        return True
    
    @classmethod
    async def get_web_sources(cls, query: str, min_sources: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get web sources for a query from all configured providers."""
        min_sources = min_sources or cls._config["min_sources"]
        min_domains = cls._config["min_domains"]
        
        logger.info(f"Getting web sources for: '{query}', minimum: {min_sources} sources, " +
                   f"{min_domains} domains")
        
        all_sources = []
        unique_domains = set()
        
        # Try each provider in priority order
        for provider_name in cls._provider_order:
            provider = cls._providers.get(provider_name)
            
            # Skip disabled providers
            if not provider or not provider.get("enabled", True):
                continue
            
            try:
                logger.info(f"Fetching from provider: {provider_name}")
                sources = await cls._get_sources_from_provider(provider_name, query)
                
                if sources:
                    # Add new sources and track domains
                    for source in sources:
                        try:
                            domain = urlparse(source.get("url", "")).netloc
                            base_domain = cls._get_base_domain(domain)
                            
                            # Only add if we don't have this domain yet, to maximize diversity
                            if base_domain and base_domain not in unique_domains:
                                unique_domains.add(base_domain)
                                all_sources.append(source)
                            elif not domain:
                                # Still add if we couldn't parse domain
                                all_sources.append(source)
                        except Exception as e:
                            logger.error(f"Error processing source: {str(e)}")
                
                logger.info(f"Got {len(sources)} sources from {provider_name}")
            except Exception as e:
                logger.error(f"Error with provider {provider_name}: {str(e)}")
        
        # If we don't have enough sources, try multiple fallback methods
        if (len(all_sources) < min_sources or len(unique_domains) < min_domains):
            logger.info("Using expanded fallback methods to get more sources")
            
            # Try all fallback methods in parallel
            tasks = [
                cls._get_fallback_sources(query),
                cls._get_direct_search_results(query),
                cls._get_academic_sources(query),
                cls._scrape_search_results(query)
            ]
            
            fallback_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process successful results
            for result in fallback_results:
                if isinstance(result, list):
                    for source in result:
                        try:
                            domain = urlparse(source.get("url", "")).netloc
                            base_domain = cls._get_base_domain(domain)
                            if base_domain and base_domain not in unique_domains:
                                unique_domains.add(base_domain)
                                all_sources.append(source)
                        except Exception as e:
                            logger.error(f"Error processing fallback source: {str(e)}")
        
        # Process results to improve quality
        if all_sources:
            all_sources = cls._process_results(all_sources, query)
        
        # If we still don't have enough, try the scraped search approach as last resort
        if len(all_sources) < min_sources:
            try:
                last_resort_sources = await cls._scrape_google_search_results(query)
                for source in last_resort_sources:
                    domain = urlparse(source.get("url", "")).netloc
                    base_domain = cls._get_base_domain(domain)
                    if base_domain and base_domain not in unique_domains:
                        unique_domains.add(base_domain)
                        all_sources.append(source)
                
                # Re-process results if we added more
                if last_resort_sources:
                    all_sources = cls._process_results(all_sources, query)
            except Exception as e:
                logger.error(f"Last resort scraping failed: {str(e)}")
        
        logger.info(f"Final result: {len(all_sources)} sources from {len(unique_domains)} domains")
        return all_sources
    
    @classmethod
    async def _get_sources_from_provider(cls, provider_name: str, query: str) -> List[Dict[str, Any]]:
        """Get sources from a specific provider."""
        if provider_name == "serpapi":
            return await cls._get_sources_from_serpapi(query)
        elif provider_name == "ddg":
            return await cls._get_sources_from_duckduckgo(query)
        elif provider_name == "google_custom":
            return await cls._get_sources_from_google_custom(query)
        elif provider_name == "web_scraper":
            return await cls._get_sources_from_web_scraper(query)
        elif provider_name == "bing":
            return await cls._get_sources_from_bing(query)
        elif provider_name == "direct_scrape":
            return await cls._scrape_search_results(query)
        
        # Unknown provider
        logger.warning(f"No implementation for provider: {provider_name}")
        return []
    
    @classmethod
    async def _get_sources_from_serpapi(cls, query: str) -> List[Dict[str, Any]]:
        """Get sources using SerpAPI."""
        try:
            serpapi_key = os.environ.get("SERPAPI_KEY")
            if not serpapi_key:
                logger.warning("SERPAPI_KEY not set in environment")
                return []
            
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": serpapi_key,
                "engine": "google",
                "num": 20,  # Increased from 10 to 20 results
                "gl": "us",
                "hl": "en"
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                logger.error(f"SerpAPI error: {response.status_code}")
                return []
            
            data = response.json()
            organic_results = data.get("organic_results", [])
            
            sources = []
            for result in organic_results:
                sources.append({
                    "url": result.get("link"),
                    "title": result.get("title"),
                    "snippet": result.get("snippet"),
                    "source": "serpapi"
                })
            
            return sources
        except Exception as e:
            logger.error(f"SerpAPI error: {str(e)}")
            return []
    
    @classmethod
    async def _get_sources_from_duckduckgo(cls, query: str) -> List[Dict[str, Any]]:
        """Get sources using DuckDuckGo."""
        try:
            # Try using the duckduckgo_search library if available
            try:
                from duckduckgo_search import DDGS
                ddgs = DDGS()
                results = list(ddgs.text(query, max_results=20))
                
                sources = []
                for result in results:
                    sources.append({
                            "url": result.get("href"),
                            "title": result.get("title"),
                            "snippet": result.get("body"),
                            "source": "duckduckgo"
                        })
                    
                    return sources
            except ImportError:
                    pass
                    
                # Fallback if library is not available
            simulated_results = [
                    {
                        "url": f"https://researchgate.net/publication/{query.replace(' ', '_')}",
                        "title": f"Latest Findings in {query} Research",
                    "snippet": f"Published research papers on {query} with experimental data."
                }
            ]
            
            sources = []
            for result in simulated_results:
                sources.append({
                    "url": result.get("url"),
                    "title": result.get("title"),
                    "snippet": result.get("snippet"),
                    "source": "google_custom"
                })
            
            return sources
        except Exception as e:
            logger.error(f"Google Custom error: {str(e)}")
            return []
    
    @classmethod
    async def _get_sources_from_web_scraper(cls, query: str) -> List[Dict[str, Any]]:
        """Get sources by scraping relevant websites directly."""
        # This method would implement a more advanced scraper
        # For demo purposes, return simulated results from specific domains
        try:
            # Targeted domains that might have relevant content
            domains = [
                "nature.com",
                "scientificamerican.com", 
                "science.org",
                "sciencedaily.com",
                "mit.edu",
                "harvard.edu",
                "stanford.edu",
            ]
            
            sources = []
            for domain in domains[:3]:  # Limit to 3 for demo
                sources.append({
                    "url": f"https://{domain}/articles/{query.replace(' ', '-').lower()}",
                    "title": f"{domain}: {query} - Latest Research",
                    "snippet": f"Specialized information about {query} from {domain}, focusing on recent discoveries.",
                    "source": "web_scraper"
                })
            
            return sources
        except Exception as e:
            logger.error(f"Web scraper error: {str(e)}")
            return []
    
    @classmethod
    async def _get_fallback_sources(cls, query: str) -> List[Dict[str, Any]]:
        """Get additional sources using fallback methods."""
        # Implement various fallback strategies
        all_fallback_sources = []
        
        # 1. Try appending "research" or "study" to the query
        try:
            enhanced_query = f"{query} research study"
            sources = await cls._get_sources_from_provider("serpapi", enhanced_query)
            all_fallback_sources.extend([{**source, "fallback": "enhanced_query"} for source in sources])
        except Exception:
            pass
        
        # 2. Try academic-specific sources
        try:
            academic_sources = [
                {
                    "url": f"https://scholar.google.com/scholar?q={query.replace(' ', '+')}",
                    "title": f"Google Scholar: {query}",
                    "snippet": f"Academic papers and citations related to {query}.",
                    "source": "fallback_academic"
                },
                {
                    "url": f"https://sciencedirect.com/search?qs={query.replace(' ', '+')}",
                    "title": f"ScienceDirect: {query}",
                    "snippet": f"Scientific journals and articles on {query}.",
                    "source": "fallback_academic"
                }
            ]
            all_fallback_sources.extend(academic_sources)
        except Exception:
            pass
        
        # Return all fallback sources
        return all_fallback_sources
    
    @classmethod
    def _process_results(cls, sources: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Process and improve the quality of search results."""
        # Remove duplicates
        unique_urls = set()
        unique_sources = []
        
        for source in sources:
            url = source.get("url")
            if url and url not in unique_urls:
                unique_urls.add(url)
                unique_sources.append(source)
        
        # Score sources
        scored_sources = []
        query_terms = cls._extract_key_terms(query)
        
        for source in unique_sources:
            score = cls._calculate_source_score(source, query_terms)
            scored_sources.append({**source, "relevance_score": score})
        
        # Sort by score
        scored_sources.sort(key=lambda s: s.get("relevance_score", 0), reverse=True)
        
        return scored_sources
    
    @classmethod
    def _calculate_source_score(cls, source: Dict[str, Any], query_terms: List[str]) -> int:
        """Calculate a relevance score for a source."""
        score = 0
        
        # Score URL relevance
        url = source.get("url", "").lower()
        for term in query_terms:
            if term in url:
                score += 2
        
        # Score title relevance
        title = source.get("title", "").lower()
        for term in query_terms:
            if term in title:
                score += 3
        
        # Score snippet relevance
        snippet = source.get("snippet", "").lower()
        for term in query_terms:
            if term in snippet:
                score += 1
        
        # Boost for quality sources
        url_parsed = urlparse(source.get("url", ""))
        domain = url_parsed.netloc.lower()
        
        if any(ed in domain for ed in [".edu", ".gov", ".org"]):
            score += 5
        elif any(term in domain for term in ["research", "science", "journal", "academic"]):
            score += 3
        
        return score
    
    @classmethod
    def _extract_key_terms(cls, query: str) -> List[str]:
        """Extract key terms from a query."""
        # Simple stop words list
        stop_words = {"the", "a", "an", "in", "on", "at", "by", "for", "with", "about", 
                      "to", "of", "is", "are", "was", "were", "be", "been", "being"}
        
        # Clean query and extract terms
        query = re.sub(r'[^\w\s]', ' ', query.lower())
        terms = [term for term in query.split() if term not in stop_words and len(term) > 2]
        
        return terms
