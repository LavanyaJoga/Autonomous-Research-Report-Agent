import os
import re
import requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import trafilatura
from urllib.parse import urlparse
import markdown
import time
from datetime import datetime
import json

# Try to import NLP libraries with fallbacks
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class ContentProcessor:
    """
    Processes web content for research purposes:
    - Extracts content from web pages
    - Summarizes content
    - Analyzes and structures information
    - Generates formatted reports
    """
    
    def __init__(self):
        """Initialize the content processor."""
        self.client = OpenAI() if OPENAI_AVAILABLE else None
        self.extracted_cache = {}  # Cache extracted content
    
    def extract_content_from_url(self, url: str) -> str:
        """
        Extract main content from a web page.
        
        Args:
            url: The URL to extract content from
            
        Returns:
            Extracted text content
        """
        # Check cache first
        if url in self.extracted_cache:
            return self.extracted_cache[url]
            
        try:
            # Use a browser-like User-Agent
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Get the web page
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Try trafilatura first (best for article content)
            extracted_text = trafilatura.extract(response.text)
            
            # If trafilatura fails, fall back to BeautifulSoup
            if not extracted_text:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()
                
                # Get text
                extracted_text = soup.get_text(separator=' ', strip=True)
                
                # Clean up whitespace
                extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
            
            # Cache the result
            self.extracted_cache[url] = extracted_text
            
            return extracted_text
            
        except Exception as e:
            print(f"Error extracting content from {url}: {str(e)}")
            return ""
    
    def summarize_content(self, content: str, max_length: int = 200) -> str:
        """
        Summarize content using NLP.
        
        Args:
            content: The text content to summarize
            max_length: Maximum length of summary
            
        Returns:
            Summarized text
        """
        if not content:
            return ""
            
        # Try OpenAI first (best quality)
        if OPENAI_AVAILABLE and self.client:
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a research assistant. Summarize the following content concisely."},
                        {"role": "user", "content": f"Summarize this content in about {max_length} words:\n\n{content[:4000]}"}
                    ],
                    max_tokens=max_length,
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"OpenAI summarization failed: {str(e)}")
        
        # Fall back to spaCy if available
        if SPACY_AVAILABLE:
            try:
                # Process the text with spaCy
                doc = nlp(content[:10000])  # Limit input size
                
                # Extract sentences
                sentences = [sent.text.strip() for sent in doc.sents]
                
                # Take the first few sentences as a simple summary
                summary_sentences = sentences[:3]
                summary = " ".join(summary_sentences)
                
                # Truncate if too long
                if len(summary) > max_length:
                    summary = summary[:max_length] + "..."
                    
                return summary
            except Exception as e:
                print(f"spaCy summarization failed: {str(e)}")
        
        # Simplest fallback: just take the first part of the text
        if len(content) > max_length:
            return content[:max_length] + "..."
        return content
    
    def analyze_content(self, content: str, query: str) -> Dict[str, Any]:
        """
        Analyze content to extract key information related to the query.
        
        Args:
            content: The text content to analyze
            query: The original research query
            
        Returns:
            Dict with analysis results
        """
        if not content:
            return {"relevance": 0, "key_points": []}
            
        # Use OpenAI for best analysis if available
        if OPENAI_AVAILABLE and self.client:
            try:
                analysis_prompt = f"""
                Analyze the following text content in relation to the research query: "{query}"
                
                Content: {content[:4000]}
                
                Please provide:
                1. Relevance score (0-10)
                2. Key points (max 5)
                3. Any factual data or statistics
                4. Quoted text that directly answers the query (if any)
                
                Format your response as JSON with these fields.
                """
                
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a research analyst. Extract structured information from content."},
                        {"role": "user", "content": analysis_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                
                result_text = response.choices[0].message.content.strip()
                
                # Parse the JSON response
                try:
                    analysis = json.loads(result_text)
                    return analysis
                except json.JSONDecodeError:
                    # Fall back to extracting information from the text response
                    analysis = {
                        "relevance": 5,
                        "key_points": [line.strip() for line in result_text.split('\n') if line.strip().startswith('-')],
                        "quotes": result_text
                    }
                    return analysis
                    
            except Exception as e:
                print(f"OpenAI analysis failed: {str(e)}")
        
        # Fallback analysis
        return {
            "relevance": 5,  # Medium relevance by default
            "key_points": [content[:100] + "..."],
            "quotes": content[:200] + "..."
        }
    
    def generate_report(self, query: str, sources: List[Dict[str, Any]], 
                        subtopics: List[str], output_dir: str, include_citations: bool = True) -> Dict[str, str]:
        """
        Generate a complete research report from analyzed sources.
        
        Args:
            query: The original research query
            sources: List of source information including analysis
            subtopics: List of subtopics to cover
            output_dir: Directory to save the report
            include_citations: Whether to include citations
            
        Returns:
            Dict with paths to generated report files
        """
        # Create timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = re.sub(r'[^\w\s]', '', query.lower()).replace(' ', '_')[:30]
        filename_base = f"{safe_query}_{timestamp}"
        
        # Create output paths
        md_path = os.path.join(output_dir, f"{filename_base}.md")
        pdf_path = os.path.join(output_dir, f"{filename_base}.pdf")
        
        # Make sure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate the report content using OpenAI if available
        if OPENAI_AVAILABLE and self.client:
            # Group sources by subtopic
            sources_by_subtopic = self._group_sources_by_subtopic(sources, subtopics)
            
            # Start building the report
            report_content = f"# Research Report: {query}\n\n"
            
            # Executive summary
            try:
                summary = self._generate_executive_summary(query, sources)
                report_content += f"## Executive Summary\n\n{summary}\n\n"
            except Exception as e:
                print(f"Error generating executive summary: {str(e)}")
                report_content += f"## Executive Summary\n\nA comprehensive analysis of {query}.\n\n"
            
            # Generate content for each subtopic
            for subtopic in subtopics:
                report_content += f"## {subtopic}\n\n"
                
                # Get sources for this subtopic
                subtopic_sources = sources_by_subtopic.get(subtopic, [])
                
                if subtopic_sources:
                    # Generate content for this subtopic based on sources
                    try:
                        section_content = self._generate_section_content(subtopic, subtopic_sources, query)
                        report_content += section_content + "\n\n"
                    except Exception as e:
                        print(f"Error generating content for subtopic {subtopic}: {str(e)}")
                        report_content += f"Content for {subtopic} based on available sources.\n\n"
                else:
                    report_content += f"No specific sources were found for this subtopic.\n\n"
            
            # Add references section
            if include_citations:
                report_content += "## References\n\n"
                for i, source in enumerate(sources, 1):
                    title = source.get('title', 'Untitled Source')
                    url = source.get('url', '')
                    report_content += f"{i}. [{title}]({url})\n"
            
            # Write to markdown file
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            # Try to generate PDF
            try:
                self._convert_markdown_to_pdf(md_path, pdf_path)
            except Exception as pdf_error:
                print(f"Error generating PDF: {str(pdf_error)}")
                # PDF path will still be returned but might not exist
            
            return {
                "md_path": md_path,
                "pdf_path": pdf_path,
                "sections": len(subtopics),
                "sources": len(sources)
            }
        else:
            # Simplified report generation without OpenAI
            report_content = f"# Research Report: {query}\n\n"
            report_content += f"## Executive Summary\n\nA comprehensive analysis of {query}.\n\n"
            
            for subtopic in subtopics:
                report_content += f"## {subtopic}\n\n"
                report_content += f"Analysis of {subtopic} related to {query}.\n\n"
            
            # Add references
            if include_citations:
                report_content += "## References\n\n"
                for i, source in enumerate(sources, 1):
                    title = source.get('title', 'Untitled Source')
                    url = source.get('url', '')
                    report_content += f"{i}. [{title}]({url})\n"
            
            # Write to markdown file
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
                
            return {
                "md_path": md_path,
                "pdf_path": pdf_path,  # Won't exist without conversion
                "sections": len(subtopics),
                "sources": len(sources)
            }
    
    def _group_sources_by_subtopic(self, sources: List[Dict[str, Any]], subtopics: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Group sources by their relevance to each subtopic."""
        result = {subtopic: [] for subtopic in subtopics}
        
        # If OpenAI is available, use it to match sources to subtopics
        if OPENAI_AVAILABLE and self.client:
            for source in sources:
                # Skip sources without content
                if not source.get('content'):
                    continue
                    
                # For each source, determine which subtopics it's most relevant to
                try:
                    subtopic_relevance = self._match_source_to_subtopics(source, subtopics)
                    
                    # Add source to each relevant subtopic
                    for subtopic, score in subtopic_relevance.items():
                        if score > 5:  # Only add if relevance score is high enough
                            result[subtopic].append(source)
                except Exception as e:
                    print(f"Error matching source to subtopics: {str(e)}")
                    # As fallback, add to all subtopics
                    for subtopic in subtopics:
                        result[subtopic].append(source)
        else:
            # Without OpenAI, use simpler text matching
            for source in sources:
                title = source.get('title', '').lower()
                snippet = source.get('snippet', '').lower()
                
                for subtopic in subtopics:
                    subtopic_lower = subtopic.lower()
                    # Check if subtopic words appear in title or snippet
                    if any(word in title or word in snippet for word in subtopic_lower.split()):
                        result[subtopic].append(source)
        
        return result
    
    def _match_source_to_subtopics(self, source: Dict[str, Any], subtopics: List[str]) -> Dict[str, int]:
        """Match a source to subtopics and return relevance scores."""
        content = source.get('content', '')
        if not content:
            content = source.get('snippet', '')
        
        if not content:
            # No content to match, return low scores
            return {subtopic: 3 for subtopic in subtopics}
        
        # Use OpenAI to analyze relevance to each subtopic
        subtopics_text = "\n".join([f"- {subtopic}" for subtopic in subtopics])
        
        prompt = f"""
        Analyze the relevance of this content to each subtopic. 
        Content: {content[:3000]}
        
        Subtopics:
        {subtopics_text}
        
        Rate each subtopic's relevance to the content on a scale of 0-10.
        Format your response as a JSON object with subtopics as keys and scores as values.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a research analyst determining content relevance to topics."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # Parse the response
            result_text = response.choices[0].message.content.strip()
            relevance_scores = json.loads(result_text)
            
            # Ensure all subtopics have scores
            for subtopic in subtopics:
                if subtopic not in relevance_scores:
                    relevance_scores[subtopic] = 3  # Default medium-low score
                    
            return relevance_scores
            
        except Exception as e:
            print(f"Error in matching source to subtopics: {str(e)}")
            # Return default scores as fallback
            return {subtopic: 5 for subtopic in subtopics}
    
    def _generate_executive_summary(self, query: str, sources: List[Dict[str, Any]]) -> str:
        """Generate an executive summary for the report."""
        # Collect key points from the most relevant sources
        key_points = []
        
        for source in sources[:5]:  # Use top 5 sources
            analysis = source.get('analysis', {})
            if not analysis:
                continue
                
            points = analysis.get('key_points', [])
            key_points.extend(points)
        
        # Limit number of key points
        key_points = key_points[:10]
        
        # Format key points for the prompt
        key_points_text = "\n".join([f"- {point}" for point in key_points])
        
        prompt = f"""
        Generate an executive summary for a research report on: "{query}"
        
        Key points from sources:
        {key_points_text}
        
        The executive summary should:
        1. Be 3-4 paragraphs long
        2. Provide an overview of the topic
        3. Highlight the most important findings
        4. Be written in a formal, academic style
        5. Be objective and factual
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a research report writer creating executive summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating executive summary: {str(e)}")
            return f"This research report examines {query} based on multiple sources. The analysis explores key aspects and provides evidence-based insights on the topic."
    
    def _generate_section_content(self, subtopic: str, sources: List[Dict[str, Any]], query: str) -> str:
        """Generate content for a specific section based on sources."""
        # Extract quotes and key points from sources for this subtopic
        quotes = []
        key_points = []
        
        for source in sources:
            analysis = source.get('analysis', {})
            if not analysis:
                continue
                
            # Get quotes and key points
            if 'quotes' in analysis:
                quotes.append(analysis['quotes'])
            
            if 'key_points' in analysis:
                key_points.extend(analysis['key_points'])
        
        # Limit to prevent token issues
        quotes = quotes[:5]
        key_points = key_points[:8]
        
        # Format for the prompt
        quotes_text = "\n".join([f"- {quote[:200]}..." for quote in quotes])
        key_points_text = "\n".join([f"- {point}" for point in key_points])
        
        prompt = f"""
        Generate a section on "{subtopic}" for a research report about "{query}"
        
        Key points from sources:
        {key_points_text}
        
        Relevant quotes:
        {quotes_text}
        
        The section should:
        1. Be 2-3 paragraphs long
        2. Be well-structured and coherent
        3. Incorporate the key points and quotes where relevant
        4. Provide a balanced analysis
        5. Be written in a formal, academic style
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a research report writer creating comprehensive sections based on source material."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=600
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating section content: {str(e)}")
            return f"This section examines {subtopic} in relation to {query}, analyzing key aspects from multiple sources."
    
    def _convert_markdown_to_pdf(self, md_path: str, pdf_path: str) -> None:
        """Convert markdown to PDF if possible."""
        try:
            # Try to use weasyprint if available
            from weasyprint import HTML
            
            # Convert markdown to HTML first
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            html_content = markdown.markdown(md_content)
            
            # Add some basic styling
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 3cm; line-height: 1.5; }}
                    h1 {{ color: #333366; }}
                    h2 {{ color: #333366; margin-top: 1.5em; }}
                    a {{ color: #0066cc; }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            # Convert HTML to PDF
            HTML(string=styled_html).write_pdf(pdf_path)
            
        except ImportError:
            # Fallback option - try to use a markdown to PDF CLI tool if installed
            try:
                import subprocess
                subprocess.run(['mdpdf', md_path, pdf_path], check=True)
            except Exception as e:
                print(f"PDF conversion failed: {str(e)}")
                raise
