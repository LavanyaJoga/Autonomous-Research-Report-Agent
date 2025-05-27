import os
import time
import re
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus
import requests

class IntegratedResearchAgent:
    """A research agent that provides both AI-generated content and web resources in one call."""
    
    def __init__(self):
        """Initialize the integrated research agent."""
        print("Initializing IntegratedResearchAgent")
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY not found in environment variables")
    
    def get_comprehensive_results(self, query: str) -> Dict[str, Any]:
        """
        Generate a comprehensive research result including summary, subtopics and web resources.
        
        Args:
            query: The research topic
        
        Returns:
            Dictionary with summary, subtopics, and web resources
        """
        print(f"Generating comprehensive results for: {query}")
        
        try:
            # 1. Generate AI content (summary and subtopics)
            ai_content = self._generate_ai_content(query)
            summary = ai_content.get('summary', f"Summary: {query} is a topic worth exploring.")
            subtopics = ai_content.get('subtopics', [f"Overview of {query}"])
            
            # 2. Find web resources for each subtopic
            web_resources = {}
            for subtopic in subtopics:
                subtopic_results = self._search_web(subtopic, num_results=3)
                web_resources[subtopic] = subtopic_results
                
                # Avoid rate limiting
                time.sleep(0.5)
            
            # 3. Find general resources for the main query
            general_resources = self._search_web(query, num_results=5)
            web_resources["General Resources"] = general_resources
            
            return {
                "query": query,
                "summary": summary,
                "subtopics": subtopics,
                "web_resources": web_resources,
                "status": "success"
            }
            
        except Exception as e:
            print(f"Error generating comprehensive results: {str(e)}")
            return {
                "query": query,
                "summary": f"Summary: {query} is a topic that requires thorough research.",
                "subtopics": [f"Aspects of {query}", f"Applications of {query}"],
                "web_resources": {},
                "status": "error",
                "error": str(e)
            }
    
    def _generate_ai_content(self, query: str) -> Dict[str, Any]:
        """Generate AI content (summary and subtopics) for the query."""
        try:
            from openai import OpenAI
            client = OpenAI()
            
            # Generate summary
            summary_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a research assistant providing concise, factual summaries."},
                    {"role": "user", "content": f"Provide a 2-3 sentence factual summary about '{query}'. Start with 'Summary: '"}
                ],
                temperature=0.2,
                max_tokens=200
            )
            summary = summary_response.choices[0].message.content.strip()
            
            # Generate subtopics with the improved prompt for specificity
            subtopics_prompt = f"""
            Create 4-6 specific section headings for a research report on "{query}".
            
            Requirements:
            1. Each heading must specifically mention key terms from "{query}"
            2. Avoid generic headings like "Introduction to X" or "Overview of X"
            3. Make headings specific, detailed, and directly relevant to the topic
            4. Cover different aspects of the topic
            5. Return ONLY the numbered list of headings, nothing else
            """
            
            subtopics_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a research assistant creating specific, detailed outlines."},
                    {"role": "user", "content": subtopics_prompt}
                ],
                temperature=0.3,
                max_tokens=400
            )
            
            # Extract and clean subtopics
            subtopics_text = subtopics_response.choices[0].message.content.strip()
            subtopics = []
            
            for line in subtopics_text.split('\n'):
                if not line.strip():
                    continue
                # Extract everything after the number
                match = re.match(r'^\d+\.?\s*(.+)$', line.strip())
                if match:
                    subtopic = match.group(1).strip()
                    if subtopic:
                        subtopics.append(subtopic)
            
            return {
                "summary": summary,
                "subtopics": subtopics
            }
            
        except Exception as e:
            print(f"Error generating AI content: {str(e)}")
            return {
                "summary": f"Summary: {query} is a topic that requires exploration.",
                "subtopics": [
                    f"Key Aspects of {query}",
                    f"Applications of {query}",
                    f"Future of {query}"
                ]
            }
    
    def _search_web(self, query: str, num_results: int = 3) -> List[Dict[str, str]]:
        """Search for web resources related to the query."""
        try:
            # Clean query for search
            clean_query = self._prepare_search_query(query)
            url_encoded_query = quote_plus(clean_query)
            
            # Try to use web search agent if available
            try:
                from app.agents.web_search_agent import WebSearchAgent
                web_agent = WebSearchAgent()
                results = web_agent.search_web(query, num_results=num_results)
                if results:
                    return results
            except Exception as web_agent_error:
                print(f"WebSearchAgent search failed: {str(web_agent_error)}")
            
            # If WebSearchAgent failed or isn't available, try Wikipedia API
            try:
                wiki_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={url_encoded_query}&limit={num_results}&namespace=0&format=json"
                response = requests.get(wiki_url)
                results = []
                if response.status_code == 200:
                    data = response.json()
                    for i in range(min(len(data[1]), num_results)):
                        if i < len(data[1]) and i < len(data[3]):
                            results.append({
                                'title': data[1][i],
                                'url': data[3][i],
                                'snippet': f"Wikipedia article about {data[1][i]}"
                            })
                    if results:
                        return results
            except Exception as wiki_error:
                print(f"Wikipedia search failed: {str(wiki_error)}")
            
            # If all else fails, generate reliable topic-specific URLs
            keywords = clean_query.split()
            if len(keywords) == 0:
                keywords = [query]
                
            # Create keyword combinations for better URLs
            plus_keywords = "+".join(keywords)
            
            # Add some reliable domains with search URLs
            domains = [
                {"name": "Wikipedia", "url": f"https://en.wikipedia.org/wiki/Special:Search?search={plus_keywords}"},
                {"name": "Britannica", "url": f"https://www.britannica.com/search?query={plus_keywords}"},
                {"name": "BBC", "url": f"https://www.bbc.co.uk/search?q={plus_keywords}"},
                {"name": "New York Times", "url": f"https://www.nytimes.com/search?query={plus_keywords}"},
                {"name": "Google Scholar", "url": f"https://scholar.google.com/scholar?q={plus_keywords}"},
                {"name": "JSTOR", "url": f"https://www.jstor.org/action/doBasicSearch?Query={plus_keywords}"},
                {"name": "Reuters", "url": f"https://www.reuters.com/search/news?blob={plus_keywords}"},
                {"name": "Al Jazeera", "url": f"https://www.aljazeera.com/search/{plus_keywords}"}
            ]
            
            results = []
            for domain in domains:
                results.append({
                    'title': f"{query} - {domain['name']}",
                    'url': domain['url'],
                    'snippet': f"Information about {query} from {domain['name']}"
                })
                if len(results) >= num_results:
                    break
            
            return results[:num_results]
            
        except Exception as e:
            print(f"Error searching web: {str(e)}")
            return []
    
    def _prepare_search_query(self, query: str) -> str:
        """Prepare a query for search by removing unnecessary words and formatting."""
        # Remove punctuation 
        query = re.sub(r'[?!.,;:]', '', query.lower())
        
        # Remove common filler words while preserving structure
        stopwords = ['what', 'is', 'are', 'how', 'to', 'the', 'a', 'an', 'in', 'on', 'of', 'for', 'tell', 'me', 'about']
        words = query.split()
        
        # For special topics like wars, keep important terms
        if 'war' in words or 'conflict' in words:
            important_terms = ['india', 'pakistan', 'china', 'russia', 'ukraine', 'usa', 'us', 'japan', 
                           'korea', 'vietnam', 'iraq', 'iran', 'afghanistan', 'israel', 'palestine',
                           'civil', 'world', 'cold', 'gulf', 'war', 'conflict']
            key_words = []
            for word in words:
                if word not in stopwords or word in important_terms:
                    key_words.append(word)
            
            # If we have enough important words, use them
            if len(key_words) >= 2:
                return ' '.join(key_words)
        
        # Standard processing for other queries
        key_words = [word for word in words if word not in stopwords and len(word) > 2]
        
        # If we filtered too much, use more of the original words
        if len(key_words) < 2 and len(words) >= 2:
            return ' '.join(words)
        
        return ' '.join(key_words)
