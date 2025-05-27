from typing import List, Dict, Any, Optional
import os
import re
import requests
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
import time

# Import LangChain components with updated imports
try:
    # Updated imports for LangChain 0.2.0+
    from langchain_community.chat_models import ChatOpenAI
    from langchain.agents import initialize_agent, Tool
    from langchain.agents import AgentType
    from langchain.chains.summarize import load_summarize_chain
    from langchain.prompts import PromptTemplate
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.chains import LLMChain
    from langchain.docstore.document import Document
    LANGCHAIN_AVAILABLE = True
except ImportError:
    try:
        # Fallback to older imports
        from langchain.chat_models import ChatOpenAI
        from langchain.agents import initialize_agent, Tool
        from langchain.agents import AgentType
        from langchain.chains.summarize import load_summarize_chain
        from langchain.prompts import PromptTemplate
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.chains import LLMChain
        from langchain.docstore.document import Document
        LANGCHAIN_AVAILABLE = True
        print("WARNING: Using deprecated LangChain imports. Consider upgrading to langchain-community.")
    except ImportError:
        LANGCHAIN_AVAILABLE = False
        print("LangChain not available. Install with: pip install -U langchain langchain-community")

class LangChainSearchAgent:
    """
    An agent that uses LangChain and external search to find information about topics,
    extract content from web pages, and summarize the information.
    """
    
    def __init__(self):
        """Initialize the LangChain search agent."""
        # Get User-Agent from environment variables or use default
        self.user_agent = os.environ.get(
            "USER_AGENT", 
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Log a warning if USER_AGENT is not set
        if "USER_AGENT" not in os.environ:
            print("WARNING: USER_AGENT environment variable not set, consider setting it to identify your requests.")
        
        # Create LangChain components if available
        if LANGCHAIN_AVAILABLE:
            try:
                self.llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-16k")
                
                # Define tools for the agent
                self.tools = [
                    Tool(
                        name="Search",
                        func=self.search_web,
                        description="Useful for searching the web to find information about topics."
                    ),
                    Tool(
                        name="ExtractContent",
                        func=self.extract_content,
                        description="Useful for extracting content from a webpage given its URL."
                    ),
                    Tool(
                        name="SummarizeContent",
                        func=self.summarize_content,
                        description="Useful for summarizing content from a webpage."
                    )
                ]
                
                # Initialize the agent
                self.agent = initialize_agent(
                    self.tools,
                    self.llm,
                    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                    verbose=True
                )
                
                # Initialize summarization chain
                self.summarize_chain = load_summarize_chain(
                    llm=self.llm,
                    chain_type="map_reduce",
                    verbose=True
                )
                
                print("LangChain search agent initialized successfully")
            except Exception as e:
                print(f"Error initializing LangChain components: {str(e)}")
                self.agent = None
        else:
            self.agent = None
    
    def search_web(self, query: str) -> str:
        """
        Search the web for information about a query.
        Returns search results in a structured format.
        
        Args:
            query: The search query
            
        Returns:
            A string with formatted search results
        """
        search_results = []
        
        # Try Google search
        try:
            google_results = self._search_google(query, num_results=5)
            search_results.extend(google_results)
        except Exception as e:
            print(f"Google search error: {str(e)}")
        
        # Try DuckDuckGo search
        try:
            ddg_results = self._search_duckduckgo(query, num_results=5)
            search_results.extend(ddg_results)
        except Exception as e:
            print(f"DuckDuckGo search error: {str(e)}")
        
        # Deduplicate results
        unique_results = []
        seen_urls = set()
        
        for result in search_results:
            url = result.get('url')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)
        
        # Format results for return
        formatted_results = []
        for i, result in enumerate(unique_results[:10]):  # Limit to top 10
            formatted_results.append(
                f"[{i+1}] {result.get('title', 'No Title')}\n"
                f"URL: {result.get('url', 'No URL')}\n"
                f"Snippet: {result.get('snippet', 'No snippet available')}\n"
            )
        
        if formatted_results:
            return "Search Results:\n\n" + "\n".join(formatted_results)
        else:
            return "No search results found."
    
    def extract_content(self, url: str) -> str:
        """
        Extract the main content from a webpage.
        
        Args:
            url: The URL to extract content from
            
        Returns:
            The extracted text content
        """
        try:
            # Make request to the URL
            headers = {'User-Agent': self.user_agent}
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type:
                return f"Cannot extract content from non-HTML page: {content_type}"
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
                tag.decompose()
            
            # Try to find main content
            main_content = None
            
            # Try common content containers
            content_selectors = [
                'article', 'main', '.content', '#content', '.post', '.entry-content', 
                '[role="main"]', '.article', '.post-content'
            ]
            
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    main_content = elements[0]
                    break
            
            # If no main content found, use body
            if not main_content:
                main_content = soup.body
            
            # Extract paragraphs
            if main_content:
                paragraphs = main_content.find_all('p')
                
                # If no paragraphs found, get divs that might contain text
                if not paragraphs:
                    paragraphs = main_content.find_all('div')
                
                # Extract text from paragraphs
                texts = []
                for p in paragraphs:
                    text = p.get_text().strip()
                    if len(text) > 40:  # Skip very short paragraphs
                        texts.append(text)
                
                # Join all paragraph texts
                content = "\n\n".join(texts)
                
                # Clean up whitespace
                content = re.sub(r'\s+', ' ', content).strip()
                
                # Truncate if too long
                if len(content) > 8000:
                    content = content[:8000] + "... [content truncated]"
                
                return content
            else:
                return "Could not identify main content in the webpage."
        
        except Exception as e:
            return f"Error extracting content: {str(e)}"
    
    def summarize_content(self, content: str) -> str:
        """
        Summarize the provided content using LangChain.
        
        Args:
            content: The text content to summarize
            
        Returns:
            A summary of the content
        """
        if not LANGCHAIN_AVAILABLE or not self.llm:
            return "LangChain not available for summarization."
        
        try:
            # Split the content into chunks if it's too long
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=4000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            docs = [Document(page_content=chunk) for chunk in text_splitter.split_text(content)]
            
            # Run the summarization chain
            try:
                # Use invoke() instead of run() (for newer LangChain versions)
                summary = self.summarize_chain.invoke(docs)
            except AttributeError:
                # Fallback to run() method for older versions
                summary = self.summarize_chain.run(docs)
            
            return summary
        
        except Exception as e:
            return f"Error during summarization: {str(e)}"
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Full processing pipeline: search for query, extract content from top results,
        and summarize the content.
        
        Args:
            query: The search query
            
        Returns:
            A dictionary with search results and processed information
        """
        results = {
            "query": query,
            "search_results": [],
            "error": None
        }
        
        try:
            # If LangChain agent is available, use it
            if LANGCHAIN_AVAILABLE and self.agent:
                try:
                    # Use invoke method for newer versions
                    agent_response = self.agent.invoke(
                        {"input": f"Find information about '{query}', extract content from top results, and provide summaries."}
                    )
                    results["agent_response"] = agent_response.get("output", "")
                except AttributeError:
                    # Fallback to run for older versions
                    agent_response = self.agent.run(
                        f"Find information about '{query}', extract content from top results, and provide summaries."
                    )
                    results["agent_response"] = agent_response
            
            # Regardless of LangChain, always perform direct search as fallback/supplement
            search_results = []
            
            # Try Google search
            google_results = self._search_google(query, num_results=5)
            search_results.extend(google_results)
            
            # Try DuckDuckGo search
            ddg_results = self._search_duckduckgo(query, num_results=5)
            search_results.extend(ddg_results)
            
            # Deduplicate results
            unique_results = []
            seen_urls = set()
            
            for result in search_results:
                url = result.get('url')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)
            
            # Process top 5 results
            processed_results = []
            for i, result in enumerate(unique_results[:5]):
                try:
                    url = result.get('url')
                    print(f"Processing result {i+1}: {url}")
                    
                    # Extract content
                    content = self.extract_content(url)
                    
                    # Summarize content
                    summary = ""
                    if content and len(content) > 100:
                        if LANGCHAIN_AVAILABLE and self.llm:
                            summary = self.summarize_content(content)
                        else:
                            # Simple summary: first 200 characters
                            summary = content[:200] + "..."
                    
                    processed_results.append({
                        "title": result.get('title', 'No Title'),
                        "url": url,
                        "snippet": result.get('snippet', ''),
                        "summary": summary,
                        "content_length": len(content) if content else 0
                    })
                    
                except Exception as e:
                    print(f"Error processing result {url}: {str(e)}")
            
            results["search_results"] = processed_results
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def _search_google(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Search Google directly."""
        try:
            # Encode query for URL
            encoded_query = quote_plus(query)
            url = f"https://www.google.com/search?q={encoded_query}&num={num_results}&hl=en"
            
            # Set up headers
            headers = {
                'User-Agent': self.user_agent,
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            # Make request
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the results
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for g in soup.find_all('div', class_='g'):
                # Extract title
                title_elem = g.find('h3')
                if not title_elem:
                    continue
                    
                title = title_elem.get_text()
                
                # Extract URL
                a_tag = g.find('a')
                if not a_tag:
                    continue
                    
                link = a_tag.get('href', '')
                
                # Clean URL
                if link.startswith('/url?q='):
                    link = link[7:]
                    link = link.split('&sa=')[0]
                
                # Extract snippet
                snippet_elem = g.find('div', class_='VwiC3b')
                snippet = snippet_elem.get_text() if snippet_elem else ""
                
                results.append({
                    'title': title,
                    'url': link,
                    'snippet': snippet,
                    'source': 'google'
                })
                
                if len(results) >= num_results:
                    break
            
            return results
            
        except Exception as e:
            print(f"Google search error: {str(e)}")
            return []
    
    def _search_duckduckgo(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """Direct DuckDuckGo search scraping."""
        try:
            # Encode query for URL
            encoded_query = quote_plus(query)
            url = f"https://duckduckgo.com/html/?q={encoded_query}"
            
            # Set up headers
            headers = {'User-Agent': self.user_agent}
            
            # Make request
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find results
            results = []
            for result in soup.select('.result'):
                # Extract title
                title_elem = result.select_one('.result__title')
                url_elem = result.select_one('.result__url')
                snippet_elem = result.select_one('.result__snippet')
                
                if title_elem and url_elem:
                    title = title_elem.get_text().strip()
                    url = url_elem.get('href') if url_elem.has_attr('href') else ""
                    snippet = snippet_elem.get_text().strip() if snippet_elem else ""
                    
                    # Clean URL
                    if url.startswith('/'):
                        url = 'https://duckduckgo.com' + url
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'snippet': snippet,
                        'source': 'duckduckgo'
                    })
                    
                    if len(results) >= num_results:
                        break
            
            return results
            
        except Exception as e:
            print(f"DuckDuckGo search error: {str(e)}")
            return []
