"""
Simple script to start the FastAPI application with uvicorn
and perform a basic self-check to ensure the API is responding.
"""
import os
import sys
import time
import requests
import uvicorn
import threading
import webbrowser

def check_api(base_url="http://127.0.0.1:8000", retries=5, delay=1):
    """Check if the API is running by hitting the health endpoint."""
    for attempt in range(retries):
        try:
            print(f"Checking API health (attempt {attempt+1}/{retries})...")
            response = requests.get(f"{base_url}/health")
            if response.status_code == 200:
                print("✅ API is running and healthy!")
                print(f"Response: {response.json()}")
                return True
            else:
                print(f"API returned status code: {response.status_code}")
        except requests.RequestException as e:
            print(f"Error connecting to API: {str(e)}")
        
        if attempt < retries - 1:
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
    
    print("❌ Could not connect to API after multiple attempts")
    return False

def test_research_endpoint(base_url="http://127.0.0.1:8000", query="Quantum Computing"):
    """Test the research API endpoint."""
    try:
        print(f"\nTesting research API with query: '{query}'...")
        
        # Try both endpoints (with and without /api prefix)
        endpoints = [f"{base_url}/api/research", f"{base_url}/research"]
        
        for endpoint in endpoints:
            try:
                response = requests.post(
                    endpoint,
                    json={"query": query},
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"\nPOST {endpoint}")
                print(f"Status code: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    task_id = result.get("task_id", "unknown")
                    print(f"✅ Success! Task ID: {task_id}")
                    print(f"Response preview: {str(result)[:200]}...")
                    
                    # Also test the GET endpoint to retrieve task
                    time.sleep(1)  # Give backend a moment to process
                    get_response = requests.get(f"{base_url}/api/research/{task_id}")
                    if get_response.status_code == 200:
                        print(f"✅ Successfully retrieved task with GET /api/research/{task_id}")
                    else:
                        print(f"❌ Failed to retrieve task: {get_response.status_code}")
                    
                    return True
                else:
                    print(f"❌ Request failed: {response.text}")
            except requests.RequestException as e:
                print(f"❌ Error with endpoint {endpoint}: {str(e)}")
        
        print("❌ Both research endpoints failed")
        return False
        
    except Exception as e:
        print(f"❌ Error testing research endpoint: {str(e)}")
        return False

def run_server():
    """Start the uvicorn server with the FastAPI app."""
    # Set PYTHONPATH to ensure imports work correctly
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    if current_dir not in sys.path:
        sys.path.append(current_dir)
    
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("Loaded environment variables from .env file")
    except ImportError:
        print("python-dotenv not installed, skipping .env loading")
    
    # Start the server
    print("Starting FastAPI server...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

def open_browser():
    """Open the browser to the API documentation after a delay."""
    time.sleep(2)  # Wait for server to start
    webbrowser.open("http://127.0.0.1:8000/docs")
    print("\nOpened browser to API documentation")
    
    # Also run API tests
    time.sleep(1)
    check_api()
    test_research_endpoint()

if __name__ == "__main__":
    # Start browser in a separate thread
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Run the server (this will block until server stops)
    run_server()
