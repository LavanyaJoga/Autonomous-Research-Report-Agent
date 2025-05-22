from typing import List, Dict, Any
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter

def process_long_query(query: str, max_length: int = 200) -> Dict[str, Any]:
    """
    Process long queries by extracting key topics and generating optimized search queries.
    
    Args:
        query: The long research query
        max_length: Maximum length for each search query
        
    Returns:
        Dictionary containing original query, key topics, and optimized search queries
    """
    # Clean the query - remove excessive whitespace, punctuation
    clean_query = re.sub(r'\s+', ' ', query).strip()
    
    # Extract topic and focus from the query
    topic_focus = extract_topic_focus(clean_query)
    
    # If query is already short enough, return it with enhanced queries
    if len(clean_query) <= max_length:
        return {
            "original_query": query,
            "key_topics": [clean_query],
            "search_queries": generate_targeted_queries(clean_query, topic_focus)
        }
    
    # Split long query into sentences
    sentences = re.split(r'(?<=[.!?])\s+', clean_query)
    
    # Extract key topics using text splitting
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=max_length,
        chunk_overlap=20,
        length_function=len
    )
    
    chunks = text_splitter.split_text(clean_query)
    
    # Generate optimized search queries from chunks
    search_queries = []
    for chunk in chunks:
        # Extract keywords from chunk (simple implementation)
        words = re.findall(r'\b\w+\b', chunk.lower())
        # Filter common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'about', 'as'}
        keywords = [w for w in words if w not in stopwords and len(w) > 3]
        
        # Take most frequent/important keywords to form a query
        if len(keywords) > 5:
            # Get most frequent keywords
            from collections import Counter
            keyword_counts = Counter(keywords)
            top_keywords = [kw for kw, _ in keyword_counts.most_common(5)]
            search_queries.append(" ".join(top_keywords))
        else:
            # Use the whole chunk if it's already concise
            search_queries.append(chunk[:max_length])
    
    return {
        "original_query": query,
        "key_topics": chunks,
        "search_queries": search_queries
    }

def extract_topic_focus(query: str) -> Dict[str, str]:
    """
    Extract the main topic and focus aspects from a query.
    For example, "What are the different approaches to carbon capture technology and their effectiveness?"
    would give {'main_topic': 'carbon capture technology', 'focus': 'approaches, effectiveness'}
    
    Args:
        query: The research query
        
    Returns:
        Dictionary with main_topic and focus
    """
    # Remove question words and common prefixes
    cleaned = re.sub(r'^(what are|what is|how do|why do|explain|describe|discuss)\s+', '', query.lower())
    
    # Extract key terms based on common patterns
    key_terms = []
    focus_terms = []
    
    # Look for specific technology/topic patterns
    tech_match = re.search(r'(technology|technique|method|approach|system|process|mechanism)(?:s)?\s+(?:of|for|to|in)\s+([a-z\s]+)', cleaned)
    if tech_match:
        key_terms.append(tech_match.group(2).strip())
    
    # Look for "approaches to X" pattern
    approach_match = re.search(r'approaches\s+to\s+([a-z\s]+)', cleaned)
    if approach_match:
        key_terms.append(approach_match.group(1).strip())
    
    # Look for domain-specific compound terms
    domain_terms = re.findall(r'([a-z]+\s+[a-z]+\s+technology|[a-z]+\s+[a-z]+\s+system|[a-z]+\s+[a-z]+\s+method|[a-z]+\s+capture)', cleaned)
    key_terms.extend(domain_terms)
    
    # Extract focus aspects (effectiveness, comparison, etc.)
    focus_aspects = ['effectiveness', 'comparison', 'advantages', 'disadvantages', 
                     'benefits', 'limitations', 'challenges', 'impact', 'application',
                     'implementation', 'cost', 'efficiency', 'sustainability']
    
    for aspect in focus_aspects:
        if aspect in cleaned:
            focus_terms.append(aspect)
    
    # If no specific pattern matched, use important noun phrases
    if not key_terms:
        # Simple noun phrase extraction (this could be improved with NLP)
        noun_phrases = re.findall(r'([a-z]+(?:\s+[a-z]+){1,3})', cleaned)
        if noun_phrases:
            # Take longest noun phrases first, they're often more specific
            noun_phrases.sort(key=len, reverse=True)
            key_terms = noun_phrases[:2]
    
    # Combine multiple key terms if found
    main_topic = ' '.join(set(key_terms)) if key_terms else cleaned[:50]
    focus = ', '.join(set(focus_terms)) if focus_terms else ''
    
    return {
        'main_topic': main_topic,
        'focus': focus
    }

def generate_targeted_queries(query: str, topic_focus: Dict[str, str]) -> List[str]:
    """
    Generate targeted search queries based on the query and extracted topic/focus.
    
    Args:
        query: Original query
        topic_focus: Dictionary with main_topic and focus
        
    Returns:
        List of targeted search queries
    """
    main_topic = topic_focus['main_topic']
    focus = topic_focus['focus']
    
    # Start with a direct query
    queries = [query]
    
    # Add topic-specific queries
    if main_topic:
        # Add academic/technical queries
        queries.append(f"{main_topic} research paper")
        queries.append(f"{main_topic} technology review")
        
        # Add focus-specific queries
        if focus:
            for focus_term in focus.split(', '):
                if focus_term:
                    queries.append(f"{main_topic} {focus_term}")
                    
            # For effectiveness or comparison queries, add specific combinations
            if 'effectiveness' in focus or 'comparison' in focus:
                queries.append(f"comparing {main_topic} approaches")
                queries.append(f"{main_topic} effectiveness analysis")
                queries.append(f"{main_topic} different methods compared")
        
        # Add domain-specific sources for common technical domains
        if 'carbon' in main_topic or 'climate' in main_topic:
            queries.append(f"{main_topic} IPCC report")
            
        if any(term in main_topic for term in ['technology', 'engineering', 'science']):
            queries.append(f"{main_topic} scientific journal")
            queries.append(f"{main_topic} engineering perspective")
    
    # Remove duplicates and limit to 5 queries
    unique_queries = []
    for q in queries:
        if q not in unique_queries:
            unique_queries.append(q)
    
    return unique_queries[:5]

def extract_key_entities(text: str) -> List[str]:
    """
    Extract key entities (people, organizations, concepts) from text.
    A simple keyword extraction implementation.
    
    Args:
        text: Input text
        
    Returns:
        List of key entities
    """
    # This is a simplified implementation
    # In production, you might use NER (Named Entity Recognition) or topic modeling
    
    # Split into words and remove punctuation
    words = re.findall(r'\b[A-Za-z][A-Za-z\-]+\b', text)
    
    # Filter out common words
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with',
                'by', 'about', 'as', 'what', 'how', 'when', 'where', 'who', 'why', 'which'}
    candidates = [w for w in words if w.lower() not in stopwords and len(w) > 3]
    
    # Find potential entities (capitalized words or repeated terms)
    entities = set()
    
    # Add capitalized words (potential named entities)
    for word in candidates:
        if word[0].isupper() and word.lower() not in stopwords:
            entities.add(word)
    
    # Add frequently occurring terms
    from collections import Counter
    word_counts = Counter([w.lower() for w in candidates])
    common_terms = [word for word, count in word_counts.items() if count >= 2]
    entities.update(common_terms)
    
    # Convert to list and limit the number of entities
    return list(entities)[:10]  # Return top 10 entities
