"""
Web analyzer service that fetches and analyzes web content for research.
"""

import logging
import asyncio
import traceback
from typing import Dict, List, Any, Optional
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from app.services.web_content_retriever import WebContentRetriever

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebAnalyzer:
    """Service for analyzing web content and extracting relevant information."""
    
    def __init__(self):
        # Initialize web content retriever
        self.content_retriever = WebContentRetriever()
    
    async def get_research_sources(self, query: str, min_sources: int = 7) -> Dict[str, Any]:
        """
        Get comprehensive research sources for a query.
        
        Args:
            query: The search query/research topic
            min_sources: Minimum number of sources to return
            
        Returns:
            Dictionary with web resources and analyzed content
        """
        try:
            logger.info(f"Getting research sources for: '{query}'")
            
            # Get dynamic web sources
            web_sources = await self.content_retriever.get_dynamic_web_sources(query, min_sources)
            
            # Analyze content of top sources (limit to avoid too many requests)
            content_tasks = []
            for source in web_sources[:min_sources]:
                content_tasks.append(self._fetch_and_analyze_content(source))
                
            content_results = await asyncio.gather(*content_tasks, return_exceptions=True)
            
            # Process results
            content_analyses = {}
            for i, result in enumerate(content_results):
                if isinstance(result, dict) and not isinstance(result, Exception):
                    url = web_sources[i].get('url', '')
                    if url:
                        content_analyses[url] = result
                elif isinstance(result, Exception):
                    logger.error(f"Error analyzing content: {result}")
            
            return {
                "query": query,
                "web_sources": web_sources,
                "content_analyses": content_analyses
            }
            
        except Exception as e:
            logger.error(f"Error getting research sources: {e}")
            logger.error(traceback.format_exc())
            return {
                "query": query,
                "web_sources": [],
                "content_analyses": {},
                "error": str(e)
            }
    
    async def _fetch_and_analyze_content(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch and analyze the content of a web source."""
        url = source.get('url', '')
        if not url:
            return {"error": "No URL provided"}
        
        try:
            # Fetch page content
            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                logger.info(f"Fetching content from: {url}")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                }
                
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    return {"error": f"Failed to fetch page: {response.status_code}"}
                
                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract main content (customize this for better extraction)
                main_content = self._extract_main_content(soup)
                
                # Extract metadata
                metadata = {
                    "title": self._extract_title(soup),
                    "description": self._extract_description(soup),
                    "author": self._extract_author(soup),
                    "publish_date": self._extract_date(soup),
                    "domain": urlparse(url).netloc
                }
                
                # Extract summary from main content
                summary = self._generate_summary(main_content)
                
                # Return analysis result
                return {
                    "url": url,
                    "summary": summary,
                    "metadata": metadata,
                    "content_length": len(main_content)
                }
                
        except Exception as e:
            logger.error(f"Error analyzing {url}: {e}")
            return {"error": str(e), "url": url}
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content from a web page."""
        # Try to find content in common content containers
        content_selectors = [
            'article', 'main', '.content', '#content', '.post', '.entry', '.article',
            '.main-content', '[role="main"]'
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                # Remove navigation, sidebars, etc.
                for elem in content.select('nav, sidebar, .sidebar, .navigation, .nav, .comments, .ads, .advertisement, footer, header'):
                    elem.decompose()
                return content.get_text(separator=' ', strip=True)
        
        # If no content containers found, try to get text from paragraphs
        paragraphs = soup.select('p')
        if paragraphs:
            return ' '.join(p.get_text(strip=True) for p in paragraphs)
        
        # Fallback to body content
        body = soup.find('body')
        if body:
            return body.get_text(separator=' ', strip=True)
        
        # Last resort
        return soup.get_text(separator=' ', strip=True)
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the title from a web page."""
        title = soup.find('title')
        if title:
            return title.get_text(strip=True)
        
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        return "No title found"
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract the description from a web page."""
        # Try meta description first
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content']
        
        # Try Open Graph description
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc and og_desc.get('content'):
            return og_desc['content']
        
        # Try Twitter description
        twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
        if twitter_desc and twitter_desc.get('content'):
            return twitter_desc['content']
        
        # Try first paragraph
        first_p = soup.find('p')
        if first_p:
            return first_p.get_text(strip=True)[:200]
        
        return "No description found"
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract the author from a web page."""
        # Try meta author
        meta_author = soup.find('meta', attrs={'name': 'author'})
        if meta_author and meta_author.get('content'):
            return meta_author['content']
        
        # Try author tags
        author_tags = soup.select('.author, .byline, [rel="author"]')
        if author_tags:
            return author_tags[0].get_text(strip=True)
        
        return "Unknown author"
    
    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract the publication date from a web page."""
        # Try meta date
        meta_date = soup.find('meta', attrs={'property': 'article:published_time'})
        if meta_date and meta_date.get('content'):
            return meta_date['content']
        
        # Try time tags
        time_tags = soup.find_all('time')
        if time_tags:
            for time in time_tags:
                if time.get('datetime'):
                    return time['datetime']
                else:
                    return time.get_text(strip=True)
        
        # Try date classes
        date_classes = soup.select('.date, .published, .publish-date, .post-date')
        if date_classes:
            return date_classes[0].get_text(strip=True)
        
        return "Unknown date"
    
    def _generate_summary(self, content: str) -> str:
        """Generate a summary from content."""
        # For now, just take the first 500 characters as a simple summary
        if len(content) <= 500:
            return content
        
        # Take first ~500 chars but end at a period for cleaner summary
        end_idx = min(500, len(content))
        last_period = content[:end_idx].rfind('.')
        
        if last_period > 200:  # Ensure we have a reasonable summary length
            return content[:last_period+1]
        
        return content[:end_idx] + "..."
