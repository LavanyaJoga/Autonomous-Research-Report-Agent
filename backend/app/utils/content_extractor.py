"""
Utilities for extracting and processing content from URLs.
"""
import requests
from bs4 import BeautifulSoup
import re
import traceback
from typing import Dict, Any, Optional, List
import random
import time
from urllib.parse import urlparse
import os

def extract_text_from_url(url: str) -> str:
    """
    Extract text content from a URL.
    
    Args:
        url: The URL to extract text from
        
    Returns:
        Extracted text content
    """
    # First check if URL is valid
    if not url or not isinstance(url, str):
        return "Invalid URL provided"
    
    # Parse the URL to check its structure
    try:
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return "Invalid URL format"
    except Exception:
        return "Could not parse URL"
    
    # Define multiple user agents to rotate and avoid being blocked
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    ]
    
    # Try with multiple methods in case the first fails
    methods = ['GET', 'HEAD+GET']
    content = None
    
    for method in methods:
        if content:
            break
            
        try:
            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Implement different request approaches
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                content = response.text
            elif method == 'HEAD+GET':
                # First make HEAD request to check content type
                head_response = requests.head(url, headers=headers, timeout=5)
                head_response.raise_for_status()
                
                content_type = head_response.headers.get('Content-Type', '')
                if 'text/html' in content_type or 'application/xhtml+xml' in content_type:
                    response = requests.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    content = response.text
                else:
                    print(f"Skipping non-HTML content: {content_type}")
                    return f"URL contains non-HTML content ({content_type})"
        
        except requests.exceptions.HTTPError as e:
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
                print(f"HTTP Error for {url}: {status_code}")
                if status_code == 405:  # Method Not Allowed
                    # Try a different HTTP method
                    continue
                elif status_code == 403:  # Forbidden
                    return "Access forbidden (403) - Website may be blocking scraping"
                elif status_code == 404:  # Not Found
                    return "Page not found (404)"
            else:
                print(f"HTTP Error without response: {str(e)}")
        except requests.exceptions.ConnectionError:
            print(f"Connection error for {url}")
            return "Connection error - Unable to reach website"
        except requests.exceptions.Timeout:
            print(f"Timeout error for {url}")
            return "Connection timed out - Website took too long to respond"
        except requests.exceptions.TooManyRedirects:
            print(f"Too many redirects for {url}")
            return "Too many redirects - May be a broken link"
        except Exception as e:
            print(f"Error fetching {url}: {str(e)}")
            traceback.print_exc()
    
    # If we couldn't get content with any method, return an error
    if not content:
        return "Could not retrieve webpage content"
        
    # Parse HTML content
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Remove script, style, and other non-content elements
        for element in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'noscript', 'iframe', 'svg']):
            element.decompose()
        
        # Find the main content (prioritize main content blocks)
        main_content = None
        for tag in ['main', 'article', '[role="main"]', '#content', '.content', 'section']:
            if tag.startswith('#') or tag.startswith('.'):
                selector = tag
            else:
                selector = tag
            content_tag = soup.select_one(selector)
            if content_tag:
                main_content = content_tag
                break
        
        # If we couldn't find a main content block, use the whole body
        if not main_content:
            main_content = soup.body if soup.body else soup
        
        # Extract text
        text = main_content.get_text(separator='\n', strip=True)
        
        # Clean up text
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line and len(line) > 2:
                lines.append(line)
        
        text = '\n'.join(lines)
        
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'\s{2,}', ' ', text)
        
        # Return empty message if text is too short
        if len(text) < 50:
            return "Extracted content was too short to be meaningful"
            
        return text
    except Exception as e:
        print(f"Error parsing HTML from {url}: {str(e)}")
        traceback.print_exc()
        return f"Failed to parse website content: {str(e)}"

def extract_metadata_from_url(url: str) -> Dict[str, Any]:
    """
    Extract metadata (title, description, etc.) from a URL.
    
    Args:
        url: The URL to extract metadata from
        
    Returns:
        Dictionary of metadata
    """
    try:
        # Set a user agent to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Fetch content
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract metadata
        metadata = {
            'title': soup.title.string if soup.title else "No title found",
            'description': None,
            'keywords': None,
            'author': None
        }
        
        # Extract meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            property = meta.get('property', '').lower()
            content = meta.get('content', '')
            
            if name == 'description' or property == 'og:description':
                metadata['description'] = content
            elif name == 'keywords':
                metadata['keywords'] = content
            elif name == 'author':
                metadata['author'] = content
        
        return metadata
    except Exception as e:
        print(f"Error extracting metadata from {url}: {str(e)}")
        return {
            'title': "Error extracting metadata",
            'description': f"Error: {str(e)}",
            'error': str(e)
        }

def get_page_summary(url: str, text: Optional[str] = None) -> str:
    """
    Generate a summary of a webpage using LLM.
    
    Args:
        url: The URL of the webpage
        text: The extracted text content (optional, will be extracted if not provided)
        
    Returns:
        Summary of the webpage
    """
    try:
        from openai import OpenAI
        
        # Extract text if not provided
        if not text:
            text = extract_text_from_url(url)
        
        if not text or len(text) < 50:
            return "Could not extract meaningful content from this URL."
        
        # Truncate text if too long
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        # Get metadata
        metadata = extract_metadata_from_url(url)
        title = metadata.get('title', 'Unknown Title')
        
        # Use OpenAI to summarize
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes web content accurately and concisely."},
                {"role": "user", "content": f"Please summarize the following content from {title} ({url}) in 3-4 sentences. Focus on the key points and main information:\n\n{text}"}
            ],
            max_tokens=200,
            temperature=0.3
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error summarizing page {url}: {str(e)}")
        traceback.print_exc()
        return f"Could not summarize content due to an error: {str(e)}"

def extract_keywords(text: str, n: int = 5) -> List[str]:
    """
    Extract the most important keywords from text.
    
    Args:
        text: The text to extract keywords from
        n: Number of keywords to extract
        
    Returns:
        List of keywords
    """
    try:
        from openai import OpenAI
        
        # Truncate text if too long
        max_chars = 5000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        # Use OpenAI to extract keywords
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use less expensive model for simple task
            messages=[
                {"role": "system", "content": "You are a specialized assistant that extracts the most important keywords from text."},
                {"role": "user", "content": f"Extract exactly {n} most important keywords from this text. Return ONLY the keywords separated by commas, no explanation or other text:\n\n{text}"}
            ],
            max_tokens=50,
            temperature=0.2
        )
        
        keyword_text = response.choices[0].message.content
        keywords = [k.strip() for k in keyword_text.split(',')]
        return keywords[:n]  # Ensure we don't return more than requested
    except Exception as e:
        print(f"Error extracting keywords: {str(e)}")
        # Fallback to simple word frequency
        words = re.findall(r'\b\w+\b', text.lower())
        stop_words = {'the', 'and', 'is', 'of', 'to', 'a', 'in', 'that', 'it', 'with', 'for', 'as', 'was', 'on', 'are', 'be'}
        word_counts = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                if word in word_counts:
                    word_counts[word] += 1
                else:
                    word_counts[word] = 1
        
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:n]]

# Add a new function for more robust web fetching
def fetch_url_content(url: str) -> Dict[str, Any]:
    """
    Fetch content from a URL with robust error handling and multiple fallbacks.
    
    Args:
        url: The URL to fetch content from
        
    Returns:
        Dictionary containing the text content, success status, and error message if any
    """
    max_retries = 3
    retry_delay = 2  # seconds
    
    for attempt in range(max_retries):
        try:
            # Add delay between retries to avoid rate limiting
            if attempt > 0:
                time.sleep(retry_delay)
                
            # First try to get metadata to check if the URL is accessible
            metadata = extract_metadata_from_url(url)
            if 'error' in metadata:
                print(f"Metadata error on attempt {attempt+1}: {metadata['error']}")
                continue
                
            # Then extract the full text content
            content = extract_text_from_url(url)
            
            # Check if we got an error message instead of actual content
            if content.startswith("Failed to") or content.startswith("Error") or content.startswith("Could not"):
                print(f"Content error on attempt {attempt+1}: {content}")
                if attempt < max_retries - 1:
                    continue
            
            return {
                "url": url,
                "title": metadata.get('title', 'Unknown Title'),
                "description": metadata.get('description', ''),
                "content": content,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            print(f"Error on attempt {attempt+1} for {url}: {str(e)}")
            if attempt == max_retries - 1:
                return {
                    "url": url,
                    "title": "Error",
                    "description": "",
                    "content": "",
                    "success": False,
                    "error": str(e)
                }
                
    return {
        "url": url,
        "title": "Failed after multiple attempts",
        "description": "",
        "content": "",
        "success": False,
        "error": "Maximum retry attempts reached"
    }

# Add a simpler function to get a pre-formatted summary
def get_url_summary(url: str) -> str:
    """
    Get a formatted summary of a URL's content.
    
    Args:
        url: The URL to summarize
        
    Returns:
        A formatted summary string
    """
    try:
        result = fetch_url_content(url)
        
        if not result["success"] or not result["content"]:
            return f"Failed to fetch summary: {result.get('error', 'Unknown error')}"
        
        summary = get_page_summary(url, result["content"])
        
        # Format the summary nicely
        return f"## {result['title']}\n\n{summary}\n\nSource: {url}"
    except Exception as e:
        return f"Failed to fetch summary: {str(e)}"
