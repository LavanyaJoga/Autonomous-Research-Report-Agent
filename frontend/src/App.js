import React, { useState, useEffect } from 'react';
import './App.css';

// Header component with ResearchGPT branding with classic styling
const Header = ({ title }) => {
  return (
    <header className="bg-gradient-to-r from-slate-700 to-slate-900 text-white shadow-lg py-6 border-b border-amber-500">
      <div className="container mx-auto px-4 flex items-center justify-between">
        <h1 className="text-2xl font-serif font-bold flex items-center">
          <svg className="w-8 h-8 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 6V2M12 6C10.3431 6 9 7.34315 9 9C9 10.6569 10.3431 12 12 12M12 6C13.6569 6 15 7.34315 15 9C15 10.6569 13.6569 12 12 12M12 12V22M7 2H4C2.89543 2 2 2.89543 2 4V20C2 21.1046 2.89543 22 4 22H20C21.1046 22 22 21.1046 22 20V4C22 2.89543 21.1046 2 20 2H17" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          {title}
        </h1>
      </div>
    </header>
  );
};

// Research prompt and submission component
const ResearchForm = ({ onSubmit, isLoading, onGenerateQueries, isGeneratingQueries }) => {
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (query.trim().length < 10) {
      setError('Research prompt must be at least 10 characters long');
      return;
    }
    
    setError('');
    onSubmit(query);
  };

  // Clear button handler
  const handleClear = () => {
    setQuery('');
    setError('');
  };

  // Handle text input changes
  const handleQueryChange = (e) => {
    setQuery(e.target.value);
  };

  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-8">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Research Topic</h2>
      
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <div className="relative">
            <textarea
              className="w-full px-4 py-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
              rows="4"
              placeholder="Enter your research topic (e.g., 'How does solar geoengineering work?')"
              value={query}
              onChange={handleQueryChange}
              disabled={isLoading || isGeneratingQueries}
              required
            ></textarea>
            
            {/* Clear button - keep this */}
            {query && (
              <button
                type="button"
                onClick={handleClear}
                className="absolute top-2 right-2 text-gray-400 hover:text-gray-600 focus:outline-none"
                title="Clear input"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 001.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </button>
            )}
          </div>
          <div className="mt-1 text-sm text-gray-500">
            Enter a clear, specific research question (minimum 10 characters).
          </div>
        </div>
        
        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-md border border-red-200">
            {error}
          </div>
        )}
        
        <div className="flex flex-wrap gap-4">
          <button
            type="submit"
            className={`flex items-center justify-center px-6 py-2 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
              isLoading || isGeneratingQueries
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white transition-colors'
            }`}
            disabled={isLoading || isGeneratingQueries}
          >
            {isLoading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Researching...
              </>
            ) : (
              'Submit Research Topic'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

// Search queries component
const SearchQueries = ({ queries, isLoading }) => {
  if (!queries && !isLoading) return null;
  
  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-8">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">
        Generated Search Queries
      </h2>
      
      {isLoading ? (
        <div className="flex justify-center items-center py-8">
          <svg className="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="ml-3 text-gray-600">Generating search queries...</span>
        </div>
      ) : (
        <div className="space-y-2">
          {queries.map((query, index) => (
            <div key={index} className="p-3 bg-gray-50 rounded-md border border-gray-200">
              <p className="text-gray-700">{query}</p>
            </div>
          ))}
          
          <div className="mt-4 pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              These search queries will be used to find relevant information for your research topic.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

// Research progress component
const ResearchProgress = ({ currentStep, steps }) => {
  const progress = (currentStep / steps.length) * 100;
  
  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-8 border-t-4 border-green-600">
      <h2 className="text-xl font-serif font-semibold text-gray-800 mb-4 border-b pb-2">Research Progress</h2>
      
      <div className="w-full bg-gray-200 rounded-full h-2.5 mb-6">
        <div 
          className="bg-green-600 h-2.5 rounded-full transition-all duration-500" 
          style={{ width: `${progress}%` }}
        ></div>
      </div>
      
      <div className="space-y-3">
        {steps.map((step, index) => (
          <div 
            key={index}
            className={`p-3 rounded-md flex items-center justify-between transition-colors ${
              currentStep === index + 1 
                ? 'bg-blue-50 border-l-4 border-blue-500' 
                : currentStep > index + 1 
                  ? 'bg-green-50 border-l-4 border-green-500'
                  : 'bg-gray-50'
            }`}
          >
            <span className="font-medium">
              {index + 1}. {step}
            </span>
            <span>
              {currentStep === index + 1 && (
                <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              {currentStep > index + 1 && (
                <svg className="h-5 w-5 text-green-600" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// Research results component
const ResearchResults = ({ research }) => {
  // Add useEffect with console log to monitor when component renders with new data
  React.useEffect(() => {
    console.log("ResearchResults rendering with summary:", research.summary);
  }, [research]);

  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-8 border-t-4 border-indigo-600">
      <h2 className="text-xl font-serif font-semibold text-gray-800 mb-4 border-b pb-2">Research Results</h2>
      
      <div className="bg-blue-50 border border-blue-100 rounded-lg p-5 mb-6 shadow-inner">
        <h3 className="text-lg font-serif font-medium text-gray-800 mb-3">Executive Summary</h3>
        {/* Add a key to force re-render */}
        <p key={`summary-${Date.now()}`} className="text-gray-700 leading-relaxed italic">{research.summary}</p>
      </div>
      
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-gray-600 font-serif">{research.stats}</p>
      </div>
    </div>
  );
};

// Web resources component
const WebResources = ({ taskId, isLoading, onResourcesLoaded }) => {
  const [webResources, setWebResources] = useState([]);
  const [resourcesLoading, setResourcesLoading] = useState(false);
  const [error, setError] = useState(null);
  const [urlSummaries, setUrlSummaries] = useState({});
  const [summaryLoadingStates, setSummaryLoadingStates] = useState({});
  
  // Add a ref to track if we've called onResourcesLoaded already
  const resourcesLoadedRef = React.useRef(false);

  // Fetch web resources when taskId changes
  useEffect(() => {
    if (!taskId) return;

    const fetchWebResources = async () => {
      setResourcesLoading(true);
      try {
        // Add a timestamp to prevent caching
        const timestamp = Date.now();
        const response = await fetch(`http://localhost:8000/api/research/${taskId}/web-resources?t=${timestamp}`, {
          headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
          },
        });
        
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }
        
        const data = await response.json();
        
        // Clear any previous resources first
        setWebResources({});
        setUrlSummaries({});
        
        // Modified filtering approach to ensure we get 6-7 resources
        let filteredResources = {};
        
        // Helper function to get domain from URL
        const getDomain = (url) => {
          try {
            const hostname = new URL(url).hostname;
            // Get base domain without subdomains
            const parts = hostname.split('.');
            if (parts.length > 2) {
              return parts.slice(-2).join('.');
            }
            // Remove www. prefix if present
            return hostname.replace(/^www\./, '');
          } catch {
            return url; // Return the URL if parsing fails
          }
        };
        
        // Process resources and filter by domain
        if (data.resources_by_subtopic) {
          // For each subtopic, allow up to 2 resources per domain to ensure we get enough
          Object.entries(data.resources_by_subtopic).forEach(([subtopic, resources]) => {
            const domainCounts = {};
            const uniqueResources = [];
            
            resources.forEach(resource => {
              const domain = getDomain(resource.url);
              domainCounts[domain] = (domainCounts[domain] || 0) + 1;
              
              // Add resource if we have fewer than 2 from this domain
              if (domainCounts[domain] <= 2) {
                uniqueResources.push(resource);
              }
              
              // Limit to 7 resources per subtopic
              if (uniqueResources.length >= 7) {
                return;
              }
            });
            
            filteredResources[subtopic] = uniqueResources;
          });
          
          setWebResources(filteredResources);
        } else if (data.resources) {
          // Handle flat structure with domain filtering
          const domainCounts = {};
          const uniqueResources = [];
          
          data.resources.forEach(resource => {
            const domain = getDomain(resource.url);
            domainCounts[domain] = (domainCounts[domain] || 0) + 1;
            
            // Add resource if we have fewer than 2 from this domain
            if (domainCounts[domain] <= 2) {
              uniqueResources.push(resource);
            }
            
            // Limit to 7 resources total
            if (uniqueResources.length >= 7) {
              return;
            }
          });
          
          setWebResources({
            "Main Resources": uniqueResources
          });
        }
        
        // If URL summaries are included in the response, use them
        if (data.url_summaries) {
          setUrlSummaries(data.url_summaries);
        }
        
        // After setting webResources and urlSummaries, call the callback if provided
        if (onResourcesLoaded) {
          onResourcesLoaded(filteredResources, data.url_summaries || {});
        }
      } catch (err) {
        console.error("Error fetching web resources:", err);
        setError("Failed to fetch relevant web resources");
      } finally {
        setResourcesLoading(false);
      }
    };

    fetchWebResources();
  }, [taskId, onResourcesLoaded]);

  // Automatically fetch summaries for URLs that don't have them
  useEffect(() => {
    if (!webResources || Object.keys(webResources).length === 0) return;

    // Collect all URLs that need summaries
    const urlsToFetch = [];
    
    // For each subtopic and its resources, check if we need summaries
    Object.values(webResources).forEach(resources => {
      resources.forEach(resource => {
        if (!urlSummaries[resource.url] && !summaryLoadingStates[resource.url]) {
          urlsToFetch.push(resource.url);
        }
      });
    });


      // Function to fetch summary for a URL
      const fetchUrlSummary = async (url) => {
          // Skip if already fetching or if we already have the summary
          if (summaryLoadingStates[url] || urlSummaries[url]) return;

          // Mark as loading
          setSummaryLoadingStates(prev => ({
              ...prev,
              [url]: true
          }));

          try {
              const encodedUrl = encodeURIComponent(url);
              const response = await fetch(`http://localhost:8000/api/summarize-url?url=${encodedUrl}`);

              if (!response.ok) {
                  throw new Error(`Server returned ${response.status}`);
              }

              const data = await response.json();

              // Update the URL summaries
              setUrlSummaries(prev => ({
                  ...prev,
                  [url]: data.summary || "No summary available."
              }));
          } catch (err) {
              console.error("Error fetching URL summary:", err);
              setUrlSummaries(prev => ({
                  ...prev,
                  [url]: `Failed to fetch summary: ${err.message}`
              }));
          } finally {
              setSummaryLoadingStates(prev => ({
                  ...prev,
                  [url]: false
              }));
          }
      };


    // Fetch summaries for up to 3 URLs at a time to avoid overwhelming the server
    const fetchBatch = urlsToFetch.slice(0, 3);
    
    if (fetchBatch.length > 0) {
      fetchBatch.forEach(url => fetchUrlSummary(url));
    }
  }, [webResources, urlSummaries, summaryLoadingStates]);


  // Call the onResourcesLoaded prop when resources are loaded - with debouncing
  useEffect(() => {
    // Only call if we have resources to share and haven't already triggered this data
    if ((Object.keys(webResources).length > 0 || Object.keys(urlSummaries).length > 0) && onResourcesLoaded) {
      // Use a debounce mechanism to prevent multiple rapid updates
      const handler = setTimeout(() => {
        // Only call if we haven't already sent this exact data
        const currentData = JSON.stringify({ resources: webResources, summaries: urlSummaries });
        if (resourcesLoadedRef.current !== currentData) {
          resourcesLoadedRef.current = currentData;
          onResourcesLoaded(webResources, urlSummaries);
        }
      }, 300);
      
      return () => clearTimeout(handler);
    }
  }, [webResources, urlSummaries, onResourcesLoaded]);

  if (!taskId) return null;
  
  if (resourcesLoading) {
    return (
      <div className="bg-white shadow-md rounded-lg p-6 mb-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Web Resources</h2>
        <div className="flex justify-center items-center py-8">
          <svg className="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <span className="ml-3 text-gray-600">Searching for relevant web resources...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white shadow-md rounded-lg p-6 mb-8">
        <h2 className="text-xl font-semibold text-gray-800 mb-4">Web Resources</h2>
        <div className="bg-red-50 border border-red-200 text-red-600 p-4 rounded-md">
          {error}
        </div>
      </div>
    );
  }

  if (Object.keys(webResources).length === 0) {
    return null;
  }

  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-8 border-t-4 border-blue-600">
      <h2 className="text-xl font-serif font-semibold text-gray-800 mb-4 border-b pb-2">Relevant Web Resources</h2>
      
      {Object.entries(webResources).map(([subtopic, resources]) => (
        <div key={subtopic} className="mb-8">
          <h3 className="text-lg font-serif font-medium text-gray-800 mb-4 pl-2 border-l-4 border-blue-500">{subtopic}</h3>
          
          <ul className="space-y-6">
            {resources.map((resource, index) => (
              <li key={index} className="border border-gray-200 bg-gray-50 rounded-md p-5 hover:shadow-md transition-shadow duration-200">
                <div>
                  <a 
                    href={resource.url} 
                    className="text-blue-700 font-medium hover:underline text-lg font-serif" 
                    target="_blank" 
                    rel="noopener noreferrer"
                  >
                    {resource.title || 'Untitled Resource'}
                  </a>
                </div>
                
                <p className="text-sm text-gray-600 mt-2 mb-3 italic">
                  {resource.snippet || 'No description available'}
                </p>
                
                {/* Always show summary section with enhanced styling */}
                <div className="mt-4 bg-blue-50 p-4 rounded-md border border-blue-100 shadow-inner">
                  <h4 className="text-sm font-serif font-medium text-blue-800 mb-2 border-b border-blue-200 pb-1">Summary:</h4>
                  {summaryLoadingStates[resource.url] ? (
                    <div className="flex items-center text-sm text-gray-500">
                      <svg className="animate-spin h-4 w-4 mr-2 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      <span>Generating summary...</span>
                    </div>
                  ) : urlSummaries[resource.url] ? (
                    <p className="text-sm text-gray-700 leading-relaxed">{urlSummaries[resource.url]}</p>
                  ) : (
                    <p className="text-sm text-gray-500 italic">Summary will appear here shortly...</p>
                  )}
                </div>
                
                <div className="flex items-center mt-4 text-xs text-gray-500">
                  <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l-1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd"></path>
                  </svg>
                  <span className="truncate max-w-xs">{new URL(resource.url).hostname}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

// ComprehensiveReport component
const ComprehensiveReport = ({ research, webResources, urlSummaries }) => {
  const [report, setReport] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationComplete, setGenerationComplete] = useState(false);
  
  const generateSimpleReport = () => {
    setIsGenerating(true);
    
    try {
      // Create report structure without relying on subtopics
      let reportContent = `# Comprehensive Report on ${research.query}\n\n`;
      reportContent += `## Executive Summary\n${research.summary}\n\n`;
      
      // Add a section that includes ALL URL summaries organized by source
      reportContent += '## Source Summaries\n\n';
      
      if (Object.keys(urlSummaries || {}).length > 0) {
        Object.entries(urlSummaries).forEach(([url, summaryData], index) => {
          try {
            const domain = new URL(url).hostname;
            const title = typeof summaryData === 'object' && summaryData.title ? 
              summaryData.title : `Source ${index + 1}`;
            const summaryText = typeof summaryData === 'string' ? 
              summaryData : (summaryData.summary || 'No summary available');
            
            reportContent += `### ${title} (${domain})\n\n`;
            reportContent += `${summaryText}\n\n`;
            reportContent += `[View source](${url})\n\n`;
            reportContent += '---\n\n';
          } catch (error) {
            console.error(`Error processing URL ${url}:`, error);
          }
        });
      } else {
        reportContent += 'No source summaries available.\n\n';
      }
      
      // Add references/sources section
      reportContent += '## References\n\n';
      Object.keys(urlSummaries || {}).forEach((url, index) => {
        try {
          const hostname = new URL(url).hostname;
          reportContent += `${index + 1}. [${hostname}](${url})\n`;
        } catch (error) {
          reportContent += `${index + 1}. [Source ${index + 1}](${url})\n`;
        }
      });
      
      setReport(reportContent);
      setGenerationComplete(true);
    } catch (error) {
      console.error("Error generating comprehensive report:", error);
      setReport(`Failed to generate report: ${error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // Add function to count summaries for display in button
  const getSummaryCount = () => {
    return Object.keys(urlSummaries || {}).length;
  };

  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-8 border-t-4 border-purple-600">
      <h2 className="text-xl font-serif font-semibold text-gray-800 mb-4 border-b pb-2">Comprehensive Report</h2>
      
      {!generationComplete ? (
        <div className="text-center py-6">
          <p className="text-gray-700 mb-4 font-serif">
            Generate a comprehensive report based on all collected sources and summaries.
            {getSummaryCount() > 0 && (
              <span className="block mt-2 text-blue-600">
                {getSummaryCount()} source summaries available for inclusion.
              </span>
            )}
          </p>
          <button
            onClick={generateSimpleReport}
            className="px-6 py-2 bg-purple-600 text-white rounded-md shadow hover:bg-purple-700 transition-colors font-serif mr-4"
            disabled={isGenerating}
          >
            {isGenerating ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Generating...
              </>
            ) : (
              `Generate Report with All Summaries (${getSummaryCount()})`
            )}
          </button>
        </div>
      ) : (
        <div className="mt-4">
          <div className="border rounded-md p-4 bg-gray-50 overflow-auto max-h-[600px]">
            {report.split('\n').map((line, index) => {
              if (line.startsWith('# ')) {
                return <h1 key={index} className="text-2xl font-bold font-serif mb-4">{line.substring(2)}</h1>;
              } else if (line.startsWith('## ')) {
                return <h2 key={index} className="text-xl font-bold font-serif mt-6 mb-3 text-purple-800">{line.substring(3)}</h2>;
              } else if (line.startsWith('### ')) {
                return <h3 key={index} className="text-lg font-bold font-serif mt-4 mb-2 text-purple-700">{line.substring(4)}</h3>;
              } else if (line.startsWith('**Source:')) {
                return <p key={index} className="my-2 text-blue-700 font-bold font-serif">{line}</p>;
              } else if (line === '---') {
                return <hr key={index} className="my-4 border-gray-300" />;
              } else if (line.startsWith('[View source]')) {
                return <p key={index} className="my-2">
                  <a href={line.match(/\((.*?)\)/)[1]} 
                     target="_blank" 
                     rel="noopener noreferrer"
                     className="text-blue-600 hover:underline">
                    View original source
                  </a>
                </p>;
              } else if (line === '') {
                return <div key={index} className="my-2"></div>;
              } else {
                return <p key={index} className="my-2 text-gray-800 font-serif">{line}</p>;
              }
            })}
          </div>
          
          <div className="mt-6 flex justify-between items-center">
            <div className="text-sm text-gray-600">
              <span className="font-medium">Sources included: </span>
              {Object.keys(urlSummaries || {}).length}
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => {
                  const blob = new Blob([report], { type: 'text/markdown' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `${research.query.replace(/\s+/g, '_')}_report.md`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                }}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 rounded-md"
              >
                Download as Markdown
              </button>
              <button
                onClick={generateSimpleReport}
                className="px-4 py-2 bg-purple-100 hover:bg-purple-200 text-purple-800 rounded-md"
              >
                Regenerate Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Main App component
function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingQueries, setIsGeneratingQueries] = useState(false);
  const [error, setError] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [researchResults, setResearchResults] = useState(null);
  const [searchQueries, setSearchQueries] = useState(null);
  const [webResources, setWebResources] = useState({});
  const [urlSummaries, setUrlSummaries] = useState({});

  // Research steps
  const researchSteps = [
    "Planning research",
    "Gathering sources for first sub-topic",
    "Gathering sources for second sub-topic",
    "Gathering sources for third sub-topic",
    "Gathering sources for fourth sub-topic",
    "Generating research report",
    "Finalizing report",
  ];

  // Memoize the callback function to avoid recreating it on every render
  const handleResourcesLoaded = React.useCallback((resources, summaries) => {
    setWebResources(resources);
    setUrlSummaries(summaries);
  }, []);

  const clearAllResearchData = () => {
    setResearchResults(null);
    setWebResources({});
    setUrlSummaries({});
    setTaskId(null);
    setCurrentStep(0);
    // Also clear any stored data in local storage if applicable
    localStorage.removeItem('lastResearchResults');
    localStorage.removeItem('lastTaskId');
    
    // Clear API caches
    fetch('http://localhost:8000/api/clear-cache', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    .then(response => response.json())
    .then(data => console.log("Cache cleared:", data))
    .catch(error => console.error("Error clearing cache:", error));
  };

  useEffect(() => {
    // If we have a taskId, poll for results
    if (taskId && isLoading) {
      // Add a timeout to prevent infinite loading state
      const maxPollingTime = 180000; // 3 minutes
      const pollingStartTime = Date.now();
      
      const pollInterval = setInterval(async () => {
        try {
          // Check if we've been polling too long
          if (Date.now() - pollingStartTime > maxPollingTime) {
            setError("Research is taking longer than expected. Please try again later.");
            setIsLoading(false);
            clearInterval(pollInterval);
            return;
          }
          
          console.log(`Polling status for task ${taskId}...`);
          
          // Add unique timestamp to prevent caching
          const timestamp = Date.now();
          const response = await fetch(`http://localhost:8000/api/research/${taskId}?_=${timestamp}`, {
            headers: {
              'Cache-Control': 'no-cache, no-store, must-revalidate',
              'Pragma': 'no-cache',
            },
          });
          
          if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
          }
          
          const data = await response.json();
          console.log("Task status response:", data);
          
          // Validate the status field exists and has a valid value
          if (!data.status) {
            throw new Error("Response missing status field");
          }
          
          if (data.status === "completed") {
            // Force a clean copy of the data to break reference equality
            const freshResults = JSON.parse(JSON.stringify(data));
            console.log("Setting fresh research results:", freshResults.summary);
            
            // Use a callback to ensure state gets updated correctly
            setResearchResults(() => freshResults);
            setIsLoading(false);
            setCurrentStep(researchSteps.length);
            clearInterval(pollInterval);
          } else if (data.status === "pending") {
            // Update progress if available
            if (data.current_step) {
              setCurrentStep(data.current_step);
            }
          } else if (data.status === "error") {
            // Handle error state
            setError(data.message || "Research failed with an unknown error");
            setIsLoading(false);
            clearInterval(pollInterval);
          } else {
            // Unknown status
            setError(`Research failed: Unrecognized status "${data.status}"`);
            setIsLoading(false);
            clearInterval(pollInterval);
          }
        } catch (err) {
          console.error("Error polling research status:", err);
          setError(`Failed to check research status: ${err.message}`);
          setIsLoading(false);
          clearInterval(pollInterval);
        }
      }, 2000);
      
      return () => clearInterval(pollInterval);
    }
  }, [taskId, isLoading, researchSteps.length]);

  const handleSubmit = async (query) => {
    setIsLoading(true);
    setError(null);
    clearAllResearchData(); // Clear all previous data
    
    try {
      // Include timestamp and unique ID to ensure fresh results
      const uniqueId = Date.now().toString() + Math.random().toString(36).substring(2, 9);
      console.log("Starting research with query:", query);
      
      const response = await fetch('http://localhost:8000/api/research', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': uniqueId,
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
        },
        body: JSON.stringify({ 
          query,
          timestamp: Date.now(),
          requestId: uniqueId 
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }
      
      const data = await response.json();
      console.log("Research task started:", data);
      
      if (!data.task_id) {
        throw new Error("Server response missing task ID");
      }
      
      setTaskId(data.task_id);
      setCurrentStep(1); // Starting the first step
      
      // Show immediate results if available
      if (data.immediate_results) {
        console.log("Received immediate results:", data.immediate_results);
      }
    } catch (err) {
      console.error("Error starting research:", err);
      setError(`Failed to start research: ${err.message}`);
      setIsLoading(false);
    }
  };

  // Add a retry button functionality
  const handleRetry = () => {
    console.log("Retrying research...");
    setError(null);
    setIsLoading(false);
    clearAllResearchData();
  };

  const handleGenerateQueries = async (query) => {
    setIsGeneratingQueries(true);
    setError(null);
    setSearchQueries(null);
    
    try {
      const response = await fetch(`http://localhost:8000/api/search-queries?query=${encodeURIComponent(query)}`);
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }
      
      const data = await response.json();
      
      // Parse the search queries string into an array
      let queries = [];
      if (typeof data.search_queries === 'string') {
        // Extract the numbered list from the response
        const lines = data.search_queries.split('\n');
        queries = lines
          .filter(line => /^\d+\./.test(line.trim()))
          .map(line => line.replace(/^\d+\.\s*/, '').trim());
      } else if (Array.isArray(data.search_queries)) {
        queries = data.search_queries;
      }
      
      setSearchQueries(queries);
    } catch (err) {
      setError(`Failed to generate search queries: ${err.message}`);
    } finally {
      setIsGeneratingQueries(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100">
      <Header title="Research-Report-Agent" />
      
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <section className="mb-8">
            <h2 className="text-3xl font-bold font-serif text-slate-800 mb-2">Autonomous Research & Report Agent</h2>
            <p className="text-slate-600 mb-6 font-serif leading-relaxed border-l-4 border-amber-500 pl-4 italic">
              Enter a research topic below, and our AI agent will autonomously research the topic and generate a comprehensive report with citations.
            </p>
            
            {/* Error component updated styling */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 text-red-700">
                <p className="font-medium font-serif">Error</p>
                <p className="font-serif">{error}</p>
                <button 
                  onClick={handleRetry}
                  className="mt-2 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-md transition-colors font-serif"
                >
                  Try Again
                </button>
              </div>
            )}
            
            <ResearchForm 
              onSubmit={handleSubmit} 
              isLoading={isLoading} 
              onGenerateQueries={handleGenerateQueries}
              isGeneratingQueries={isGeneratingQueries}
            />
            
            <SearchQueries 
              queries={searchQueries} 
              isLoading={isGeneratingQueries} 
            />
          </section>
          
          {isLoading && (
            <section>
              <ResearchProgress currentStep={currentStep} steps={researchSteps} />
              
              {/* Add web resources component */}
              {taskId && <WebResources 
                taskId={taskId} 
                isLoading={isLoading}
                onResourcesLoaded={handleResourcesLoaded} 
              />}
              
              {/* Add a cancel button */}
              <div className="text-center mt-4">
                <button
                  onClick={handleRetry}
                  className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-md transition-colors"
                >
                  Cancel Research
                </button>
                <p className="text-sm text-gray-500 mt-2">
                  Research may take several minutes to complete.
                </p>
              </div>
            </section>
          )}
          
          {researchResults && (
            <section>
              {/* Add a more specific key that includes the summary */}
              <ResearchResults 
                key={`research-${researchResults.query}-${researchResults.summary?.substring(0, 20)}`} 
                research={researchResults} 
              />
              <WebResources 
                taskId={taskId} 
                isLoading={false} 
                onResourcesLoaded={handleResourcesLoaded}
              />
              <ComprehensiveReport 
                key={`report-${researchResults.query}`}
                research={researchResults} 
                webResources={webResources}
                urlSummaries={urlSummaries}
              />
            </section>
          )}
        </div>
      </main>

      <footer className="bg-slate-900 text-white py-6 border-t border-amber-500">
        <div className="container mx-auto px-4 text-center">
          <p className="font-serif">&copy; {new Date().getFullYear()} ResearchGPT - Autonomous Research & Report Agent</p>
        </div>
      </footer>
    </div>
  );
}

export default App;