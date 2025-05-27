import os
import re
import time
from typing import Dict, Any, List, Optional

class SimpleResearchAgent:
    """A simplified version of the research agent for when LangChain is not available."""
    
    def __init__(self):
        """Initialize the simple research agent."""
        print("Initializing SimpleResearchAgent")
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("Warning: OPENAI_API_KEY not found in environment variables")
    
    def research_topic(self, topic: str) -> Dict[str, Any]:
        """
        Research a topic and return structured results.
        
        Args:
            topic: The research topic
            
        Returns:
            Dictionary with research results
        """
        print(f"Researching topic: {topic}")
        
        # First, let's extract keywords from the topic
        keywords = self._extract_keywords(topic)
        print(f"Extracted keywords: {keywords}")
        
        # Generate search queries based on the keywords
        search_queries = self._generate_search_queries(topic, keywords)
        print(f"Generated search queries: {search_queries}")
        
        # Use OpenAI API for summarization and subtopics
        try:
            import openai
            from openai import OpenAI
            
            client = OpenAI(api_key=self.api_key)
            
            # Generate subtopics
            subtopics_prompt = (
                f"Research topic: {topic}\n\n"
                f"Based on the above research topic and these key aspects: {', '.join(keywords)}, "
                f"generate 4-6 section headings for a comprehensive research report. "
                f"The headings should specifically address '{topic}' and cover different aspects. "
                f"Return ONLY the headings as a numbered list."
            )
            
            subtopics_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a research assistant creating an outline for a research report."},
                    {"role": "user", "content": subtopics_prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            # Extract subtopics
            subtopics_text = subtopics_response.choices[0].message.content
            subtopics = []
            for line in subtopics_text.split('\n'):
                if line.strip():
                    # Clean up the line by removing numbers and periods at the beginning
                    clean_line = re.sub(r'^\d+\.?\s*', '', line.strip())
                    if clean_line:
                        subtopics.append(clean_line)
            
            # Generate summary
            summary_response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a research assistant creating a concise summary."},
                    {"role": "user", "content": f"Provide a concise 2-3 sentence summary about '{topic}'. Start with 'Summary: '"}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            summary = summary_response.choices[0].message.content
            
            # Find web resources based on search queries
            web_resources = []
            try:
                from app.agents.web_search_agent import WebSearchAgent
                web_agent = WebSearchAgent()
                
                # Get search results for each query
                for query in search_queries[:3]:  # Limit to first 3 queries to avoid rate limits
                    print(f"Searching for web resources on: {query}")
                    results = web_agent.search_web(query, num_results=3)
                    # Make sure we don't have duplicate URLs
                    for result in results:
                        if not any(resource['url'] == result['url'] for resource in web_resources):
                            web_resources.append({
                                'title': result['title'],
                                'url': result['url'],
                                'snippet': result.get('snippet', ''),
                                'query': query
                            })
                    
                    # Small delay to prevent rate limiting
                    time.sleep(1)
            except Exception as e:
                print(f"Error getting web resources: {str(e)}")
            
            return {
                "topic": topic,
                "summary": summary,
                "subtopics": subtopics,
                "search_queries": search_queries,
                "sources": web_resources
            }
            
        except Exception as e:
            print(f"Error generating research content: {str(e)}")
            # Fallback to basic content
            return {
                "topic": topic,
                "summary": f"Summary: {topic} is a subject that requires further research and analysis.",
                "subtopics": [
                    f"Introduction to {topic}",
                    f"Key aspects of {topic}",
                    f"Applications of {topic}",
                    f"Future of {topic}"
                ],
                "search_queries": search_queries,
                "sources": []
            }
    
    def _extract_keywords(self, topic: str) -> List[str]:
        """Extract meaningful keywords from the research topic."""
        # First, clean the topic
        topic = topic.lower()
        # Remove question marks and other common punctuation
        topic = re.sub(r'[?!.,;:]', '', topic)
        # Remove common stopwords and question words
        stopwords = ['what', 'is', 'are', 'how', 'to', 'the', 'a', 'an', 'in', 'on', 'of', 'for', 'tell', 'me', 'about', 'can', 'could', 'would', 'should', 'and', 'or', 'but']
        
        # Split into words
        words = topic.split()
        # Filter out stopwords and short words
        keywords = [word for word in words if word not in stopwords and len(word) > 2]
        
        # If we didn't get any keywords, use the longest words from the original topic
        if not keywords and words:
            words_by_length = sorted(words, key=len, reverse=True)
            keywords = words_by_length[:3]
        
        # Add more context by identifying phrases
        phrases = []
        for i in range(len(words) - 1):
            if words[i] not in stopwords or words[i+1] not in stopwords:
                phrase = f"{words[i]} {words[i+1]}"
                if phrase not in phrases:
                    phrases.append(phrase)
        
        # Combine individual keywords and key phrases, limiting to 5 total
        combined = keywords.copy()
        for phrase in phrases:
            if phrase not in combined and len(combined) < 5:
                combined.append(phrase)
        
        return combined[:5]  # Limit to 5 keywords
    
    def _generate_search_queries(self, topic: str, keywords: List[str]) -> List[str]:
        """Generate search queries for the topic based on keywords."""
        # Start with direct queries based on keywords
        queries = [f"{keyword}" for keyword in keywords]
        
        # Add more specific queries
        topic_words = topic.lower().split()
        main_term = next((word for word in topic_words if word in keywords), keywords[0] if keywords else topic_words[0])
        
        # Add topic-specific query formats
        query_patterns = [
            f"what is {main_term}",
            f"{main_term} definition",
            f"{main_term} explained",
            f"{main_term} tutorial",
            f"{main_term} examples",
            f"{main_term} benefits",
            f"{main_term} vs alternatives",
            f"{main_term} use cases",
            f"how to use {main_term}",
            f"{main_term} best practices"
        ]
        
        # Combine all queries, remove duplicates, and limit to 10
        all_queries = []
        for query in queries + query_patterns:
            if query not in all_queries:
                all_queries.append(query)
        
        return all_queries[:10]
    
    def generate_search_queries(self, topic: str) -> str:
        """
        Generate specific search queries for a general research topic.
        
        Args:
            topic: The general research topic
            
        Returns:
            String with numbered list of search queries
        """
        # Extract keywords and generate search queries
        keywords = self._extract_keywords(topic)
        search_queries = self._generate_search_queries(topic, keywords)
        
        # Format as a numbered list
        result = f"Search queries for '{topic}':\n"
        for i, query in enumerate(search_queries, 1):
            result += f"{i}. {query}\n"
            
        return result
