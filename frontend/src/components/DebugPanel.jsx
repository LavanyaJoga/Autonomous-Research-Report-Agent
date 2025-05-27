import React, { useState } from 'react';

const DebugPanel = ({ taskId, lastResponse }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [apiResponse, setApiResponse] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const togglePanel = () => {
    setIsOpen(!isOpen);
  };

  const checkTaskStatus = async () => {
    if (!taskId) {
      setError("No task ID available");
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      const timestamp = Date.now();
      const response = await fetch(`http://localhost:8000/api/task-status/${taskId}?_=${timestamp}`);
      const data = await response.json();
      setApiResponse(data);
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const clearCache = async () => {
    try {
      setIsLoading(true);
      const response = await fetch('http://localhost:8000/api/clear-cache', { method: 'POST' });
      const data = await response.json();
      setApiResponse(data);
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed bottom-0 right-0 mb-4 mr-4 z-10">
      <button 
        onClick={togglePanel}
        className="bg-gray-700 hover:bg-gray-800 text-white py-2 px-4 rounded-md shadow-lg"
      >
        {isOpen ? 'Close Debug' : 'Debug'}
      </button>
      
      {isOpen && (
        <div className="bg-gray-800 text-white p-4 mt-2 rounded-md shadow-xl w-96 max-h-96 overflow-auto">
          <h3 className="text-lg font-medium mb-2">Debug Panel</h3>
          
          <div className="mb-4">
            <p className="text-sm text-gray-300">Task ID: {taskId || "None"}</p>
            <div className="flex space-x-2 mt-2">
              <button
                onClick={checkTaskStatus}
                className="bg-blue-600 hover:bg-blue-700 text-white py-1 px-3 rounded text-sm"
                disabled={!taskId || isLoading}
              >
                Check Status
              </button>
              <button
                onClick={clearCache}
                className="bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded text-sm"
                disabled={isLoading}
              >
                Clear Cache
              </button>
            </div>
          </div>
          
          {isLoading && <p className="text-gray-400">Loading...</p>}
          
          {error && (
            <div className="bg-red-900 p-2 rounded mb-2">
              <p className="text-sm">{error}</p>
            </div>
          )}
          
          {apiResponse && (
            <div>
              <h4 className="text-sm font-medium mb-1">API Response:</h4>
              <pre className="bg-gray-900 p-2 rounded text-xs overflow-x-auto">
                {JSON.stringify(apiResponse, null, 2)}
              </pre>
            </div>
          )}
          
          {lastResponse && (
            <div className="mt-4">
              <h4 className="text-sm font-medium mb-1">Last Response:</h4>
              <pre className="bg-gray-900 p-2 rounded text-xs overflow-x-auto">
                {JSON.stringify(lastResponse, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DebugPanel;
