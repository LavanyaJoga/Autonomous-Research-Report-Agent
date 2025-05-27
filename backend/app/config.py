import os
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=dotenv_path)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set OpenAI API key directly in the environment
if OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    print(f"OpenAI API key configured from config module: {OPENAI_API_KEY[:5]}...{OPENAI_API_KEY[-4:]}")
else:
    print("WARNING: OpenAI API key not found in environment variables or .env file")
