import os
import sys

def set_api_key():
    """Set the OpenAI API key as an environment variable"""
    if len(sys.argv) < 2:
        print("Usage: python set_api_key.py YOUR_API_KEY")
        return
    
    api_key = sys.argv[1]
    
    # Create or update .env file
    with open('.env', 'w') as f:
        f.write(f"OPENAI_API_KEY={api_key}\n")
        f.write(f"PYTHONPATH={os.path.abspath('.')}\n")
    
    print(f"API key saved to .env file: {api_key[:5]}...{api_key[-4:]}")
    print("You can now start the server with: python -m uvicorn app.main:app --reload")

if __name__ == "__main__":
    set_api_key()
