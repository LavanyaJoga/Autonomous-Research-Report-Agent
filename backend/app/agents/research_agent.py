import os
import re
from typing import List, Dict, Any, Optional
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains.summarize import load_summarize_chain
from langchain.chains import RetrievalQA
from langchain.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ResearchAgent:
    """LangChain agent for researching topics and summarizing content."""
    
    def __init__(self, openai_api_key: Optional[str] = None):
        """Initialize the research agent with necessary components."""
        # Set API key from env or parameter
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Please set OPENAI_API_KEY environment variable.")
        
        # Log API key status (not the actual key)
        if self.api_key.startswith("sk-"):
            print("Using OpenAI API key from environment")
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            temperature=0, 
            model="gpt-4o",
            openai_api_key=self.api_key
        )
        
        # Text splitter for document processing
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200
        )
        
        # Initialize embeddings for vector search
        self.embeddings = OpenAIEmbeddings(openai_api_key=self.api_key)
        
        # Create agent with tools
        self._create_agent()
    
    def _create_agent(self):
        """Create a LangChain agent with necessary tools."""
        tools = [
            Tool(
                name="search",
                func=self.search_tool,
                description="Search for information on a topic. Input should be a search query."
            ),
            Tool(
                name="fetch_and_summarize_webpage",
                func=self.fetch_and_summarize_webpage,
                description="Fetch content from a URL and summarize it. Input should be a URL."
            ),
            Tool(
                name="generate_search_queries",
                func=self.generate_search_queries,
                description="Generate search queries for a research topic. Input should be a research topic."
            )
        ]
        
        # Define agent prompt
        prompt = PromptTemplate.from_template(
            """You are an expert research assistant. Your goal is to find and summarize 
            information on a given topic.
            
            To do this effectively:
            1. First understand what needs to be researched
            2. Break down complex topics into specific search queries
            3. Search for relevant information
            4. Fetch and summarize content from the most promising sources
            5. Organize information logically
            
            {format_instructions}
            
            TOOLS:
            {tools}
            
            TOOL NAMES: {tool_names}
            
            TASK: {input}
            
            {agent_scratchpad}
            """
        )
        
        # Create the agent
        agent = create_react_agent(self.llm, tools, prompt)
        
        # Create the agent executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10
        )
    
    @tool
    def search_tool(self, query: str) -> str:
        """
        Search for information using web search API.
        
        Args:
            query: The search query
            
        Returns:
            Search results in string format
        """
        try:
            # Here you would typically use a search API like SerpAPI or similar
            # For now, let's return a placeholder
            # You can replace this with actual implementation using your preferred search API
            
            # Placeholder response - replace with actual search API call
            return f"Search results for '{query}':\n1. Example result 1\n2. Example result 2\n3. Example result 3"
            
            # Example using SerpAPI (if you have SERPAPI_API_KEY):
            # from langchain.utilities import SerpAPIWrapper
            # search = SerpAPIWrapper(serpapi_api_key=os.getenv("SERPAPI_API_KEY"))
            # return search.run(query)
        except Exception as e:
            return f"Error searching for '{query}': {str(e)}"
    
    @tool
    def fetch_and_summarize_webpage(self, url: str) -> str:
        """
        Fetch content from a URL and provide a summary.
        
        Args:
            url: The URL to fetch and summarize
            
        Returns:
            Summary of the webpage content
        """
        try:
            # Load webpage content
            loader = WebBaseLoader(url)
            documents = loader.load()
            
            # Split into chunks
            doc_chunks = self.text_splitter.split_documents(documents)
            
            # Create vectorstore for retrieval
            vectorstore = Chroma.from_documents(doc_chunks, self.embeddings)
            
            # Create summarization chain
            chain = load_summarize_chain(
                self.llm,
                chain_type="map_reduce",
                verbose=True
            )
            
            # Generate summary
            summary = chain.run(doc_chunks)
            
            return f"Summary of {url}:\n{summary}"
            
        except Exception as e:
            return f"Error processing URL '{url}': {str(e)}"
    
    @tool
    def generate_search_queries(self, topic: str) -> str:
        """
        Generate specific search queries for a general research topic.
        
        Args:
            topic: The general research topic
            
        Returns:
            List of specific search queries
        """
        try:
            prompt = f"""
            I'm researching the topic: "{topic}"
            
            Please generate 5-7 specific search queries that would help me gather comprehensive 
            information about this topic. The queries should:
            
            - Cover different aspects of the topic
            - Include technical and non-technical perspectives
            - Be specific enough to return focused results
            - Be diverse to gather a range of information
            
            Format the output as a numbered list.
            """
            
            response = self.llm.predict(prompt)
            return f"Search queries for '{topic}':\n{response}"
            
        except Exception as e:
            return f"Error generating search queries for '{topic}': {str(e)}"
    
    def research_topic(self, topic: str) -> Dict[str, Any]:
        """
        Research a topic comprehensively and return structured results.
        
        Args:
            topic: The research topic
            
        Returns:
            Dictionary with research results
        """
        try:
            # Get topic-specific subtopics
            subtopics = self._generate_subtopics(topic)
            
            # Get search queries
            search_queries_result = self.generate_search_queries(topic)
            search_queries = []
            
            # Parse search queries from the result
            if isinstance(search_queries_result, str):
                lines = search_queries_result.split('\n')
                for line in lines:
                    if line.strip() and re.match(r'^\d+\.', line.strip()):
                        query_text = re.sub(r'^\d+\.\s*', '', line.strip())
                        search_queries.append(query_text)
            
            # Generate a topic-specific summary
            summary = self._generate_summary(topic)
            
            # For a full implementation, we would use the agent to gather and process information
            # For now, we'll return structured results with topic-specific content
            return {
                "topic": topic,
                "summary": summary,
                "subtopics": subtopics,
                "search_queries": search_queries,
                "sources": []  # No real sources at this point
            }
        except Exception as e:
            print(f"Error in research_topic: {e}")
            import traceback
            print(traceback.format_exc())
            return {
                "topic": topic,
                "error": str(e),
                "summary": f"Research on {topic} could not be completed due to an error.",
                "subtopics": self._generate_default_subtopics(topic),
                "search_queries": [],
                "raw_result": f"Error occurred: {str(e)}"
            }
    
    def _generate_subtopics(self, topic: str) -> List[str]:
        """Generate relevant subtopics for the given research topic."""
        try:
            prompt = f"""
            I'm researching the topic: "{topic}"
            
            Please generate 4-6 subtopics that would make good sections for a 
            comprehensive research report on this topic. The subtopics should:
            
            - Cover the most important aspects of {topic}
            - Be logically organized
            - Progress from basic concepts to more advanced aspects
            - Include practical applications or implications if relevant
            
            Return just the list of subtopics, each on a new line.
            """
            
            response = self.llm.predict(prompt)
            subtopics = [line.strip() for line in response.split('\n') if line.strip()]
            return subtopics
        except Exception as e:
            print(f"Error generating subtopics: {e}")
            return self._generate_default_subtopics(topic)
    
    def _generate_default_subtopics(self, topic: str) -> List[str]:
        """Generate default subtopics if the main method fails."""
        keyword = topic.replace("?", "").strip().title()
        return [
            f"Introduction to {keyword}",
            f"Key Concepts of {keyword}",
            f"Applications of {keyword}",
            f"Advantages and Limitations of {keyword}",
            f"Future Developments in {keyword}"
        ]
    
    def _generate_summary(self, topic: str) -> str:
        """Generate a summary of the topic."""
        try:
            prompt = f"""
            Please write a concise but comprehensive summary (about 3-4 sentences) 
            of the topic: "{topic}"
            
            The summary should:
            - Explain what {topic} is
            - Highlight key aspects or components
            - Mention important applications or implications
            - Be factually accurate and informative
            
            Write just the summary paragraph, starting with "Summary: "
            """
            
            response = self.llm.predict(prompt)
            if not response.startswith("Summary:"):
                response = "Summary: " + response
            return response
        except Exception as e:
            print(f"Error generating summary: {e}")
            return f"Summary: {topic} is an important concept with multiple aspects and applications. Due to technical limitations, a detailed summary could not be generated at this time."
