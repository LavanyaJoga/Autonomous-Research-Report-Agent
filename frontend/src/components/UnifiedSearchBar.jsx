import React, { useState, useEffect } from 'react';
import axios from 'axios';

const UnifiedSearchBar = () => {
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState('quick'); // 'quick' or 'comprehensive'
  const [results, setResults] = useState([]);
  const [taskId, setTaskId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);

  // Add state for source categories and selected sources
  const [sourceCategories, setSourceCategories] = useState([]);
  const [selectedSources, setSelectedSources] = useState([]);
  const [analyzingQuery, setAnalyzingQuery] = useState(false);

  // Analyze query function to determine relevant source types
  const analyzeQuery = async (queryText) => {
    if (!queryText || queryText.length < 5) return;
    
    setAnalyzingQuery(true);
    
    try {
      // Call a new backend endpoint to analyze the query
      const response = await axios.post('/api/analyze-query', { query: queryText });
      
      if (response.data && response.data.categories) {
        setSourceCategories(response.data.categories);
        
        // Auto-select recommended sources
        if (response.data.recommended) {
          setSelectedSources(response.data.recommended);
        }
      }
    } catch (err) {
      console.error('Error analyzing query:', err);
      // Fall back to generic categories
      setSourceCategories([
        { id: 'general', name: 'General Knowledge', recommended: true },
        { id: 'academic', name: 'Academic Sources', recommended: false },
        { id: 'news', name: 'News Articles', recommended: false },
        { id: 'technical', name: 'Technical Documentation', recommended: false }
      ]);
      setSelectedSources(['general']);
    } finally {
      setAnalyzingQuery(false);
    }
  };

  // Call analyzeQuery when query changes (with debounce)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (query.trim().length >= 5) {
        analyzeQuery(query);
      }
    }, 800);
    
    return () => clearTimeout(timer);
  }, [query]);

  // Toggle source selection
  const toggleSource = (sourceId) => {
    if (selectedSources.includes(sourceId)) {
      setSelectedSources(selectedSources.filter(id => id !== sourceId));
    } else {
      setSelectedSources([...selectedSources, sourceId]);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!query.trim() || query.trim().length < 3) {
      setError('Please enter a search query (at least 3 characters)');
      return;
    }
    
    setLoading(true);
    setError('');
    setResults([]);
    setTaskId(null);
    
    try {
      if (searchType === 'quick') {
        // Quick search with selected sources
        const response = await axios.post('/api/search', { 
          query,
          sources: selectedSources.length > 0 ? selectedSources : undefined
        });
        setResults(response.data.results);
        setLoading(false);
      } else {
        // Comprehensive research using /api/research endpoint
        const response = await axios.post('/api/research', { 
          query,
          sourceCategories: selectedSources.length > 0 ? selectedSources : undefined
        });
        setTaskId(response.data.task_id);
        
        // Show immediate results if available
        if (response.data.immediate_results) {
          const immediateResults = response.data.immediate_results;
          
          // Format web resources as results
          if (immediateResults.web_resources && immediateResults.web_resources.length > 0) {
            const formattedResults = immediateResults.web_resources.map(resource => ({
              title: resource.title,
              link: resource.url,
              snippet: resource.snippet
            }));
            setResults(formattedResults);
          }
          
          // Show summary if available
          if (immediateResults.summary) {
            // Add summary as a special result at the top
            setResults(prevResults => [
              {
                title: "Research Summary",
                link: "#summary",
                snippet: immediateResults.summary,
                isSpecial: true
              },
              ...prevResults
            ]);
          }
        }
        
        // Start polling for task status
        pollTaskStatus(response.data.task_id);
      }
    } catch (err) {
      console.error('Search error:', err);
      setError(err.response?.data?.detail || 'Error performing search. Please try again.');
      setLoading(false);
    }
  };
  
  const pollTaskStatus = async (taskId) => {
    try {
      const statusResponse = await axios.get(`/api/research/${taskId}`);
      
      if (statusResponse.data.status === 'pending') {
        // Update progress if available
        if (statusResponse.data.progress) {
          setProgress(statusResponse.data.progress * 100);
        }
        
        // Continue polling after a delay
        setTimeout(() => pollTaskStatus(taskId), 2000);
      } else if (statusResponse.data.status === 'completed') {
        // Research completed, show complete results
        setLoading(false);
        
        // Format the final results
        if (statusResponse.data.sources) {
          const formattedResults = statusResponse.data.sources.map(source => ({
            title: source.title,
            link: source.url,
            snippet: source.snippet
          }));
          setResults(formattedResults);
        }
        
        // Add download links
        if (statusResponse.data.md_path) {
          setResults(prevResults => [
            {
              title: "📄 Download Research Report (Markdown)",
              link: `/api/download?path=${encodeURIComponent(statusResponse.data.md_path)}`,
              snippet: "Download the complete research report in Markdown format",
              isSpecial: true
            },
            ...prevResults
          ]);
        }
        
        if (statusResponse.data.pdf_path) {
          setResults(prevResults => [
            {
              title: "📄 Download Research Report (PDF)",
              link: `/api/download?path=${encodeURIComponent(statusResponse.data.pdf_path)}`,
              snippet: "Download the complete research report in PDF format",
              isSpecial: true
            },
            ...prevResults
          ]);
        }
      } else {
        // Handle error state
        setLoading(false);
        setError(`Research failed: ${statusResponse.data.message || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Status polling error:', err);
      setLoading(false);
      setError('Error checking research status. Please try again.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h1 className="text-3xl font-bold text-center mb-6 text-gray-800">Research Assistant</h1>
      
      <form onSubmit={handleSearch} className="mb-6">
        <div className="mb-4">
          <div className="flex flex-col md:flex-row md:items-center mb-2">
            <input
              type="text"
              className="flex-grow px-4 py-2 border border-gray-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter a research question..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
            />
            <div className="flex mt-2 md:mt-0">
              <button 
                type="submit" 
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 md:rounded-r-lg rounded-lg md:rounded-l-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                disabled={loading}
              >
                {loading ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {searchType === 'quick' ? 'Searching...' : 'Researching...'}
                  </span>
                ) : 'Search'}
              </button>
            </div>
          </div>
          
          {/* Source category selection */}
          {sourceCategories.length > 0 && (
            <div className="mt-3 mb-4">
              <p className="text-sm font-medium text-gray-700 mb-2">
                {analyzingQuery ? 'Analyzing your query...' : 'Search in these sources:'}
              </p>
              <div className="flex flex-wrap gap-2">
                {sourceCategories.map(category => (
                  <button
                    key={category.id}
                    type="button"
                    onClick={() => toggleSource(category.id)}
                    className={`text-xs px-3 py-1 rounded-full transition-colors ${
                      selectedSources.includes(category.id)
                        ? 'bg-blue-100 text-blue-800 border border-blue-300'
                        : 'bg-gray-100 text-gray-800 border border-gray-200 hover:bg-gray-200'
                    }`}
                  >
                    {selectedSources.includes(category.id) ? '✓ ' : ''}{category.name}
                  </button>
                ))}
              </div>
            </div>
          )}
          
          <div className="flex space-x-4 mt-2">
            <label className="inline-flex items-center">
              <input
                type="radio"
                className="form-radio h-4 w-4 text-blue-600"
                name="searchType"
                value="quick"
                checked={searchType === 'quick'}
                onChange={() => setSearchType('quick')}
                disabled={loading}
              />
              <span className="ml-2 text-gray-700">Quick Search</span>
            </label>
            
            <label className="inline-flex items-center">
              <input
                type="radio"
                className="form-radio h-4 w-4 text-blue-600"
                name="searchType"
                value="comprehensive"
                checked={searchType === 'comprehensive'}
                onChange={() => setSearchType('comprehensive')}
                disabled={loading}
              />
              <span className="ml-2 text-gray-700">Comprehensive Research</span>
            </label>
          </div>
        </div>
      </form>
      
      {error && (
        <div className="text-red-600 mb-4">
          {error}
        </div>
      )}
      
      {loading && (
        <div className="mb-8">
          <div className="flex justify-center my-4">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
          
          {searchType === 'comprehensive' && (
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div 
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-300" 
                style={{ width: `${progress}%` }}
              ></div>
              <p className="text-center text-sm text-gray-600 mt-2">
                {progress < 100 ? 'Generating comprehensive research report...' : 'Finalizing report...'}
              </p>
            </div>
          )}
        </div>
      )}
      
      {results.length > 0 && (
        <div className="bg-white shadow-md rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">
            {searchType === 'quick' ? '🔎 Search Results:' : '📊 Research Results:'}
          </h2>
          
          <ul className="space-y-4">
            {results.map((result, index) => (
              <li key={index} className={`${result.isSpecial ? 'bg-blue-50 p-3 rounded-lg' : 'border-b border-gray-200 pb-3 last:border-b-0'}`}>
                <div className="text-lg font-medium">
                  {index + 1}. <a href={result.link} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                    {result.title}
                  </a>
                </div>
                <div className="text-gray-600 mt-1">
                  {result.snippet}
                </div>
              </li>
            ))}
          </ul>
          
          {taskId && searchType === 'comprehensive' && (
            <div className="mt-6 pt-4 border-t border-gray-200">
              <p className="text-sm text-gray-600">
                Task ID: {taskId} • Research report generation {loading ? 'in progress' : 'completed'}
              </p>
            </div>
          )}
        </div>
      )}
      
      {!loading && results.length === 0 && query && (
        <div className="text-center my-8 text-gray-600">
          No results found. Try refining your search query.
        </div>
      )}
    </div>
  );
};

export default UnifiedSearchBar;
