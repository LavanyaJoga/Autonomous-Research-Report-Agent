import React, { useState } from 'react';
import axios from 'axios';

const SearchForm = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');


  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError('Please enter a search query');
      return;
    }
    
    setLoading(true);
    setError('');
    setResults([]);
    
    try {
      const response = await axios.post('/api/search', { query });
      setResults(response.data.results);
    } catch (err) {
      console.error('Search error:', err);
      setError(err.response?.data?.detail || 'Error performing search. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      <h1 className="text-3xl font-bold text-center mb-6 text-gray-800">Research Assistant</h1>
      
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex">
          <input
            type="text"
            className="flex-grow px-4 py-2 border border-gray-300 rounded-l-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter a research question..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          <button 
            type="submit" 
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-r-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            disabled={loading}
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Searching...
              </span>
            ) : 'Search'}
          </button>
        </div>
      </form>
      
      {error && (
        <div className="text-red-600 mb-4">
          {error}
        </div>
      )}
      
      {loading && (
        <div className="flex justify-center my-8">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      )}
      
      {results.length > 0 && (
        <div className="bg-white shadow-md rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">🔎 Search Results:</h2>
          
          <ul className="space-y-4">
            {results.map((result, index) => (
              <li key={index} className="border-b border-gray-200 pb-3 last:border-b-0">
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

export default SearchForm;
