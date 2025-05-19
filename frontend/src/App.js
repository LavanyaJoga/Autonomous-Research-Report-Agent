import React, { useState, useEffect } from 'react';
import './App.css';
import SearchForm from './components/SearchForm';
import DebugPanel from './components/DebugPanel';

// Header component with ResearchGPT branding
const Header = ({ title }) => {
  return (
    <header className="bg-gradient-to-r from-blue-600 to-indigo-700 text-white shadow-lg py-4">
      <div className="container mx-auto px-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold">{title}</h1>
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
    const currentQuery = query; // Store the query before clearing it
    setQuery(''); // Clear the input field immediately
    onSubmit(currentQuery);
  };

  const handleGenerateQueries = () => {
    if (query.trim().length < 10) {
      setError('Research prompt must be at least 10 characters long');
      return;
    }
    
    setError('');
    const currentQuery = query; // Store the query before clearing it
    setQuery(''); // Clear the input field immediately
    onGenerateQueries(currentQuery);
  };

  // Clear button handler
  const handleClear = () => {
    setQuery('');
    setError('');
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
              onChange={(e) => setQuery(e.target.value)}
              disabled={isLoading || isGeneratingQueries}
              required
              // Add a key to force input refresh
              key={`research-input-${Date.now()}`}
            ></textarea>
            
            {/* Add clear button */}
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
            type="button"
            onClick={handleGenerateQueries}
            className={`flex items-center justify-center px-4 py-2 rounded-md font-medium text-blue-600 border border-blue-600 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
              isGeneratingQueries || isLoading
                ? 'opacity-50 cursor-not-allowed'
                : 'transition-colors'
            }`}
            disabled={isGeneratingQueries || isLoading}
          >
            {isGeneratingQueries ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Generating...
              </>
            ) : (
              'Generate Search Queries'
            )}
          </button>
          
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
    <div className="bg-white shadow-md rounded-lg p-6 mb-8">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Research Progress</h2>
      
      <div className="w-full bg-gray-200 rounded-full h-2.5 mb-6">
        <div 
          className="bg-blue-600 h-2.5 rounded-full transition-all duration-500" 
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
  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-8">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Research Results</h2>
      
      <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 mb-6">
        <h3 className="text-lg font-medium text-gray-800 mb-2">Executive Summary</h3>
        <p className="text-gray-700">{research.summary}</p>
      </div>
      
      <div className="bg-gray-50 border border-gray-100 rounded-lg p-3 mb-6">
        <p className="text-sm text-gray-600">{research.stats}</p>
      </div>
      
      <h3 className="text-lg font-medium text-gray-800 mb-3">Report Sections</h3>
      <div className="space-y-4 mb-6">
        {research.subtopics.map((topic, index) => (
          <div key={index} className="border border-gray-200 rounded-lg p-4">
            <h4 className="font-medium text-gray-800">{topic}</h4>
            <p className="text-sm text-gray-500 mt-1">[Section content in full report]</p>
          </div>
        ))}
      </div>
      
      <h3 className="text-lg font-medium text-gray-800 mb-3">Download Report</h3>
      <div className="flex space-x-3">
        <a 
          href={`http://localhost:8000/api/download?path=${encodeURIComponent(research.md_path)}`} 
          className="inline-flex items-center px-4 py-2 border border-blue-600 rounded-md text-blue-600 bg-white hover:bg-blue-50 transition-colors"
          target="_blank"
          rel="noopener noreferrer"
        >
          <svg className="w-5 h-5 mr-2" fill="currentColor" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
          Markdown
        </a>
        <a 
          href={`http://localhost:8000/api/download?path=${encodeURIComponent(research.pdf_path)}`} 
          className="inline-flex items-center px-4 py-2 border border-blue-600 rounded-md text-white bg-blue-600 hover:bg-blue-700 transition-colors"
          target="_blank"
          rel="noopener noreferrer"
        >
          <svg className="w-5 h-5 mr-2" fill="currentColor" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
          PDF
        </a>
      </div>
    </div>
  );
};

// Web resources component
const WebResources = ({ taskId, isLoading }) => {
  const [webResources, setWebResources] = useState([]);
  const [resourcesLoading, setResourcesLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch web resources when taskId changes
  useEffect(() => {
    if (!taskId) return;

    const fetchWebResources = async () => {
      setResourcesLoading(true);
      try {
        // Add a timestamp to prevent caching
        const timestamp = Date.now();
        const response = await fetch(`http://localhost:8000/api/research/${taskId}/web-resources?t=${timestamp}`);
        
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }
        
        const data = await response.json();
        if (data.resources_by_subtopic) {
          setWebResources(data.resources_by_subtopic);
        }
      } catch (err) {
        console.error("Error fetching web resources:", err);
        setError("Failed to fetch relevant web resources");
      } finally {
        setResourcesLoading(false);
      }
    };

    fetchWebResources();
  }, [taskId]);

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
    <div className="bg-white shadow-md rounded-lg p-6 mb-8">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Relevant Web Resources</h2>
      
      {Object.entries(webResources).map(([subtopic, resources]) => (
        <div key={subtopic} className="mb-6">
          <h3 className="text-lg font-medium text-gray-800 mb-3">{subtopic}</h3>
          
          <ul className="space-y-3">
            {resources.map((resource, index) => (
              <li key={index} className="border border-gray-100 bg-gray-50 rounded-md p-3">
                <a href={resource.url} className="text-blue-600 font-medium hover:underline" target="_blank" rel="noopener noreferrer">
                  {resource.title || 'Untitled Resource'}
                </a>
                <p className="text-sm text-gray-600 mt-1">
                  {resource.snippet || 'No description available'}
                </p>
                <div className="flex items-center mt-2 text-xs text-gray-500">
                  <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
                    <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd"></path>
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

// Main App component
function App() {
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingQueries, setIsGeneratingQueries] = useState(false);
  const [error, setError] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [researchResults, setResearchResults] = useState(null);
  const [searchQueries, setSearchQueries] = useState(null);
  const [progress, setProgress] = useState(0);
  // Add state for lastApiResponse
  const [lastApiResponse, setLastApiResponse] = useState(null);

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
          const response = await fetch(`http://localhost:8000/api/research/${taskId}?_=${timestamp}`);
          
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
            // Validate required fields
            const requiredFields = ["query", "summary", "subtopics"];
            const missingFields = requiredFields.filter(field => !data[field]);
            
            if (missingFields.length > 0) {
              console.warn(`Completed result missing fields: ${missingFields.join(', ')}`);
              // Continue anyway - the backend should have filled in defaults
            }
            
            setResearchResults(data);
            setIsLoading(false);
            setCurrentStep(researchSteps.length);
            clearInterval(pollInterval);
          } else if (data.status === "pending") {
            // Update progress if available
            if (data.current_step) {
              setCurrentStep(data.current_step);
            }
            if (data.progress) {
              setProgress(data.progress); // Now this will work since progress state is defined
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
    setResearchResults(null);
    setCurrentStep(0);
    
    try {
      // Include timestamp and unique ID to ensure fresh results
      const uniqueId = Date.now().toString() + Math.random().toString(36).substring(2, 9);
      console.log("Starting research with query:", query);
      
      const response = await fetch('http://localhost:8000/api/research', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': uniqueId,
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
      
      // Store the API response for debugging
      setLastApiResponse(data);
      
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
    setTaskId(null);
    setCurrentStep(0);
    setResearchResults(null);
    
    // Clear any cached data
    fetch('http://localhost:8000/api/clear-cache', {
      method: 'POST',
    }).then(response => response.json())
      .then(data => console.log("Cache cleared:", data))
      .catch(error => console.error("Error clearing cache:", error));
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
    <div className="min-h-screen bg-gray-100">
      <Header title="ResearchGPT" />
      
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <section className="mb-8">
            <h2 className="text-3xl font-bold text-gray-800 mb-2">Autonomous Research & Report Agent</h2>
            <p className="text-gray-600 mb-6">
              Enter a research topic below, and our AI agent will autonomously research the topic and generate a comprehensive report with citations.
            </p>
            
            {error && (
              <div className="mb-6 p-4 bg-red-50 border-l-4 border-red-500 text-red-700">
                <p className="font-medium">Error</p>
                <p>{error}</p>
                <button 
                  onClick={handleRetry}
                  className="mt-2 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-md transition-colors"
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
              {taskId && <WebResources taskId={taskId} isLoading={isLoading} />}
              
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
              <ResearchResults research={researchResults} />
              <WebResources taskId={taskId} isLoading={false} />
            </section>
          )}
        </div>
      </main>

      <footer className="bg-gray-800 text-white py-6">
        <div className="container mx-auto px-4 text-center">
          <p>&copy; {new Date().getFullYear()} ResearchGPT - Autonomous Research & Report Agent</p>
        </div>
      </footer>
      
      {/* The DebugPanel with proper props */}
      <DebugPanel taskId={taskId} lastResponse={lastApiResponse} />
    </div>
  );
}

export default App;