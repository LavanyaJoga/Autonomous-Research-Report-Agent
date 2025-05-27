"""
Diagnostic script to identify issues with research status loading.
Run this with python diagnose.py
"""
import os
import sys
import importlib
import traceback
import json

def check_dependencies():
    """Check if all required dependencies are properly installed"""
    dependencies = [
        "fastapi", "uvicorn", "openai", "requests", "beautifulsoup4",
        "numpy", "python_dotenv", "langchain", "langchain_openai", 
        "pydantic", "typing_extensions"
    ]
    
    print("Checking dependencies:")
    for dep in dependencies:
        try:
            # Try to import each dependency
            module = importlib.import_module(dep.replace("-", "_"))
            version = getattr(module, "__version__", "unknown")
            print(f"✅ {dep}: {version}")
        except ImportError as e:
            print(f"❌ {dep}: Not installed or import error - {str(e)}")
        except Exception as e:
            print(f"⚠️ {dep}: {str(e)}")

def check_environment_variables():
    """Check if required environment variables are set"""
    print("\nChecking environment variables:")
    
    # Load .env file manually
    try:
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            print(f"Found .env file at {env_path}")
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        # Don't print the actual API key, just that it exists
                        if key == 'OPENAI_API_KEY':
                            # Check if the API key is valid (not empty or placeholder)
                            value = value.strip()
                            if not value or value == "your_api_key_here" or (not value.startswith("sk-") and len(value) < 20):
                                print(f"⚠️ {key}: Found, but appears to be invalid (too short or missing proper format)")
                            else:
                                print(f"✅ {key}: {'*' * 10}...{'*' * 5}")
                                # Also set it in the environment if not already set
                                if not os.environ.get('OPENAI_API_KEY'):
                                    os.environ['OPENAI_API_KEY'] = value
                                    print(f"   → Set {key} in environment from .env file")
                        else:
                            print(f"✅ {key}: {value}")
        else:
            print("❌ .env file not found")
    except Exception as e:
        print(f"⚠️ Error reading .env file: {str(e)}")
    
    # Check specific environment variables
    openai_key = os.environ.get('OPENAI_API_KEY')
    if openai_key:
        print(f"✅ OPENAI_API_KEY (from env): {'*' * 10}...{'*' * 5}")
    else:
        print("❌ OPENAI_API_KEY not set in environment")

def check_task_service():
    """Try to import and initialize TaskService"""
    print("\nChecking TaskService:")
    try:
        # Add the current directory to path
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        
        from app.services.task_service import TaskService
        
        # Try to create and get tasks
        test_task_id = "test-task-123"
        TaskService.create_task(
            task_id=test_task_id,
            topic="Test Task",
            parameters={"depth": "basic"}
        )
        
        tasks = TaskService.get_all_tasks()
        print(f"✅ TaskService initialized, found {len(tasks)} tasks")
        
        # Cleanup test task
        with TaskService._lock:
            if test_task_id in TaskService._tasks:
                del TaskService._tasks[test_task_id]
        
    except ImportError as e:
        print(f"❌ Could not import TaskService: {str(e)}")
    except Exception as e:
        print(f"❌ Error with TaskService: {str(e)}")
        traceback.print_exc()

def check_api_route():
    """Check if the research status API route works"""
    print("\nTesting research status API route:")
    try:
        # Import the FastAPI app and use TestClient
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/api/research/status")
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API route works")
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
        else:
            print(f"❌ API route failed with status code {response.status_code}")
            print(f"Response: {response.text}")
            
    except ImportError as e:
        print(f"❌ Could not import FastAPI app: {str(e)}")
    except Exception as e:
        print(f"❌ Error testing API route: {str(e)}")
        traceback.print_exc()

def fix_openai_api_key():
    """Attempt to fix the OPENAI_API_KEY issue by checking multiple locations and setting it"""
    print("\nAttempting to fix OPENAI_API_KEY issue:")
    
    # Check if it's already set in environment
    if os.environ.get('OPENAI_API_KEY'):
        key = os.environ.get('OPENAI_API_KEY')
        if key.startswith('sk-') or len(key) > 20:  # Simple validation
            print("✅ OPENAI_API_KEY already set in environment and appears valid")
            return True
        else:
            print("⚠️ OPENAI_API_KEY is set but appears invalid: too short or incorrect format")
    
    # Try to load from .env file
    env_paths = [
        os.path.join(os.path.dirname(__file__), '.env'),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),
        os.path.join(os.path.dirname(__file__), 'app', '.env'),
        os.path.join(os.path.expanduser('~'), '.openai'),
    ]
    
    for env_path in env_paths:
        if os.path.exists(env_path):
            print(f"Checking for OPENAI_API_KEY in {env_path}")
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                
                                # Check for variants of the API key name
                                if key.upper() in ['OPENAI_API_KEY', 'OPENAI_KEY', 'OPENAI_SECRET_KEY']:
                                    # Remove quotes if present
                                    if (value.startswith('"') and value.endswith('"')) or \
                                       (value.startswith("'") and value.endswith("'")):
                                        value = value[1:-1]
                                    
                                    if value and value != "YOUR_API_KEY_HERE" and (value.startswith('sk-') or len(value) > 20):
                                        os.environ['OPENAI_API_KEY'] = value
                                        print(f"✅ Found and set OPENAI_API_KEY from {env_path}")
                                        return True
            except Exception as e:
                print(f"⚠️ Error reading {env_path}: {str(e)}")
    
    # If we get here, we couldn't find a valid key
    print("❌ Could not find a valid OPENAI_API_KEY in any location")
    
    # Ask user to input the key
    print("\nWould you like to enter your OpenAI API key now? (it will be saved to .env)")
    response = input("Enter 'y' to continue, any other key to skip: ")
    if response.lower() == 'y':
        api_key = input("Enter your OpenAI API key (starts with 'sk-'): ")
        if api_key and (api_key.startswith('sk-') or len(api_key) > 20):
            # Save to .env file
            env_path = os.path.join(os.path.dirname(__file__), '.env')
            try:
                # Check if file exists and if OPENAI_API_KEY line is present
                if os.path.exists(env_path):
                    with open(env_path, 'r') as f:
                        lines = f.readlines()
                    
                    key_found = False
                    for i, line in enumerate(lines):
                        if line.strip().startswith('OPENAI_API_KEY='):
                            lines[i] = f'OPENAI_API_KEY={api_key}\n'
                            key_found = True
                            break
                    
                    if not key_found:
                        lines.append(f'\nOPENAI_API_KEY={api_key}\n')
                    
                    with open(env_path, 'w') as f:
                        f.writelines(lines)
                else:
                    # Create new .env file
                    with open(env_path, 'w') as f:
                        f.write(f'OPENAI_API_KEY={api_key}\n')
                
                # Set in environment
                os.environ['OPENAI_API_KEY'] = api_key
                print(f"✅ Saved API key to {env_path} and set in environment")
                return True
            except Exception as e:
                print(f"❌ Error saving API key: {str(e)}")
                # Still set it in environment for this session
                os.environ['OPENAI_API_KEY'] = api_key
                print("⚠️ Failed to save to .env file, but set in environment for this session")
                return True
        else:
            print("❌ Invalid API key format")
    
    return False

if __name__ == "__main__":
    print("=" * 50)
    print("Running diagnostic tests for Research Status API")
    print("=" * 50)
    
    check_dependencies()
    check_environment_variables()
    
    # If OPENAI_API_KEY is not set, try to fix it
    if not os.environ.get('OPENAI_API_KEY'):
        fix_openai_api_key()
    
    check_task_service()
    check_api_route()
    
    # Final check to ensure OPENAI_API_KEY is set
    if not os.environ.get('OPENAI_API_KEY'):
        print("\n⚠️ WARNING: OPENAI_API_KEY is still not set. The application may not function correctly.")
        print("You can set this by:")
        print("1. Creating a .env file in the project root with OPENAI_API_KEY=your_key")
        print("2. Setting the environment variable directly in your terminal")
        print("3. Running this diagnostic script again and entering the key when prompted")
    
    print("\nDiagnostics complete. If issues persist, please check the application logs.")
