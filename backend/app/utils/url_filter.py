"""
Enhanced URL filtering utility for improving the quality of web resources
in research applications.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class WebResourceFilter:
    """Filter web resources to find the most relevant and high-quality sources."""
    
    def __init__(self):
        """Initialize the filter with quality settings."""
        # Premium domains that are generally high quality for research
        self.premium_domains = {
            # Academic
            '.edu': 12,
            'academic': 8,
            'research': 8,
            'scholar': 8,
            'university': 7,
            
            # Government
            '.gov': 10,
            
            # Non-profit and educational
            '.org': 6,
            'wikipedia.org': 7,
            
            # Scientific publications
            'nature.com': 9,
            'science': 8,
            'sciencedirect': 8,
            'researchgate': 7,
            'springer': 7,
            'ieee': 7,
            'arxiv': 8,
        }
        
        # Domains to avoid or downrank
        self.low_quality_domains = [
            'pinterest',
            'instagram',
            'facebook',
            'twitter',
            'tiktok',
            'quora', 
            'reddit',
            'youtube',
            'tinyurl',
            'amzn',  # Amazon affiliate links
            'ebay',
            'etsy',
        ]
        
        # URL patterns to avoid
        self.avoid_paths = [
            '/login', 
            '/signin', 
            '/signup', 
            '/register',
            '/account', 
            '/cart', 
            '/checkout', 
            '/subscribe',
            '/privacy-policy', 
            '/terms-of-service', 
            '/contact',
            '/about-us', 
            '/jobs', 
            '/careers',
            '/sitemap',
            '/404',
        ]
        
        # Stop words for query processing
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 
            'were', 'be', 'been', 'being', 'to', 'of', 'for', 'with', 
            'about', 'against', 'between', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'from', 'up', 'down', 
            'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 
            'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 
            'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 
            'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 
            'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 
            'should', 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 
            'aren', 'couldn', 'didn', 'doesn', 'hadn', 'hasn', 'haven', 
            'isn', 'ma', 'mightn', 'mustn', 'needn', 'shan', 'shouldn', 
            'wasn', 'weren', 'won', 'wouldn'
        }
    
    def filter_resources(self, resources: List[Dict[str, Any]], query: str, min_sites: int = 6) -> List[Dict[str, Any]]:
        """Filter and rank resources to find the most relevant and diverse set.
        
        Args:
            resources: List of resource dictionaries with 'url', 'title', etc.
            query: The search query
            min_sites: Minimum number of unique websites to return
            
        Returns:
            Filtered and ranked list of resources
        """
        logger.info(f"Filtering resources for query: {query}")
        
        # Extract key terms from query
        query_terms = self._extract_key_terms(query)
        logger.debug(f"Extracted key terms: {', '.join(query_terms)}")
        
        if not resources:
            logger.warning("No resources to filter")
            return []
        
        # First pass: score all resources
        scored_resources = []
        domain_map = {}  # Group by domain
        
        for resource in resources:
            url = resource.get('url', '')
            if not url:
                continue
                
            try:
                # Parse URL
                parsed_url = urlparse(url)
                domain = parsed_url.netloc.lower()
                base_domain = self._get_base_domain(domain)
                path = parsed_url.path.lower()
                
                # Skip unwanted paths
                if any(avoid in path for avoid in self.avoid_paths):
                    logger.debug(f"Skipping URL with unwanted path: {url}")
                    continue
                
                # Calculate relevance score
                title = resource.get('title', '')
                snippet = resource.get('snippet', '')
                
                # Score the resource
                domain_score = self._calculate_domain_score(domain)
                relevance_score = self._calculate_relevance_score(url, title, snippet, query_terms)
                total_score = domain_score + relevance_score
                
                # Create enhanced resource with scoring info
                enhanced_resource = {
                    **resource,
                    'domain': domain,
                    'base_domain': base_domain,
                    'domain_score': domain_score,
                    'relevance_score': relevance_score,
                    'total_score': total_score,
                    'path_depth': len([p for p in path.split('/') if p])
                }
                
                # Add to scored list
                scored_resources.append(enhanced_resource)
                
                # Group by base domain
                if base_domain not in domain_map:
                    domain_map[base_domain] = []
                domain_map[base_domain].append(enhanced_resource)
                
            except Exception as e:
                logger.error(f"Error processing URL {url}: {str(e)}")
        
        # Sort all resources by score
        scored_resources.sort(key=lambda x: x['total_score'], reverse=True)
        
        # Second pass: select diverse set of resources
        filtered_resources = self._select_diverse_resources(domain_map, min_sites)
        
        # Log results
        domains_selected = len(set(r['base_domain'] for r in filtered_resources))
        logger.info(f"Selected {len(filtered_resources)} resources from {domains_selected} domains")
        
        return filtered_resources
    
    def _select_diverse_resources(self, domain_map: Dict[str, List[Dict[str, Any]]], 
                                min_sites: int) -> List[Dict[str, Any]]:
        """Select a diverse set of resources from different domains."""
        # Get the best resource from each domain
        selected_resources = []
        used_domains = set()
        
        # First, sort domains by their best score
        domain_scores = {}
        for domain, resources in domain_map.items():
            if resources:
                domain_scores[domain] = max(r['total_score'] for r in resources)
        
        # Sort domains by their best resource score
        sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Take the best resource from each domain until we meet min_sites
        for domain, _ in sorted_domains:
            if domain in used_domains:
                continue
                
            resources = domain_map[domain]
            if not resources:
                continue
                
            # Take the highest scoring resource from this domain
            best_resource = max(resources, key=lambda x: x['total_score'])
            selected_resources.append(best_resource)
            used_domains.add(domain)
            
            # Stop if we have enough domains
            if len(selected_resources) >= min_sites:
                break
        
        # If we still don't have enough resources, add more from the best domains
        if len(selected_resources) < min_sites:
            # Sort all resources by score
            all_remaining = []
            for domain, resources in domain_map.items():
                # Add remaining resources we haven't selected yet
                remaining = [r for r in resources if r not in selected_resources]
                all_remaining.extend(remaining)
            
            # Sort remaining by score
            all_remaining.sort(key=lambda x: x['total_score'], reverse=True)
            
            # Add more until we reach min_sites
            for resource in all_remaining:
                if len(selected_resources) >= min_sites:
                    break
                selected_resources.append(resource)
        
        # Final sort by total_score
        selected_resources.sort(key=lambda x: x['total_score'], reverse=True)
        
        return selected_resources
    
    def _calculate_domain_score(self, domain: str) -> int:
        """Calculate a quality score for a domain."""
        score = 0
        
        # Check premium domains
        for premium, value in self.premium_domains.items():
            if premium in domain:
                score += value
                break
        
        # Check low quality domains
        if any(bad in domain for bad in self.low_quality_domains):
            score -= 10
            
        return score
    
    def _calculate_relevance_score(self, url: str, title: str, 
                                  snippet: str, query_terms: List[str]) -> int:
        """Calculate relevance score based on query terms."""
        score = 0
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        # Check title relevance (highest importance)
        if title:
            title_lower = title.lower()
            for term in query_terms:
                if term in title_lower:
                    score += 3
                    
            # Bonus for phrase matches
            pairs = zip(query_terms, query_terms[1:])
            for term1, term2 in pairs:
                if f"{term1} {term2}" in title_lower:
                    score += 2
        
        # Check snippet relevance
        if snippet:
            snippet_lower = snippet.lower()
            for term in query_terms:
                if term in snippet_lower:
                    score += 2
        
        # Check URL path relevance
        for term in query_terms:
            if term in path:
                score += 1
                
        # Bonus for apparent content paths
        content_indicators = ['article', 'paper', 'research', 'study', 'publication', 'journal', 'report']
        if any(indicator in path for indicator in content_indicators):
            score += 3
            
        return score
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract important terms from the query."""
        # Clean the query
        query = re.sub(r'[^\w\s]', ' ', query.lower())
        
        # Remove stop words and short terms
        terms = [term for term in query.split() 
                if term not in self.stop_words and len(term) > 2]
        
        return terms
    
    def _get_base_domain(self, domain: str) -> str:
        """Extract base domain from a full domain."""
        parts = domain.split('.')
        
        # Handle special cases like co.uk, com.au
        if len(parts) > 2 and parts[-2] in ['co', 'com', 'org', 'net', 'edu', 'gov', 'ac']:
            return '.'.join(parts[-3:])
            
        # Standard case
        if len(parts) > 1:
            return '.'.join(parts[-2:])
            
        return domain
