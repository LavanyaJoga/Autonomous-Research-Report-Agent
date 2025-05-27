import time
import traceback
from datetime import datetime
import os
from typing import Dict, Any, Optional, List
from app.core.research_gpt import ResearchGPT

# Import from the app global state
from app import research_tasks

def run_research_task(task_id: str, query: str):
    """Run a research task in the background."""
    try:
        # Update task status to show it's running
        research_tasks[task_id]["status_details"] = "Starting research process..."
        print(f"Starting research task {task_id} for query: {query}")
        
        # Create research agent
        output_dir = os.path.join(os.getcwd(), "reports")
        print(f"Using output directory: {output_dir}")
        
        # Make sure the output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created output directory: {output_dir}")
        
        # Initialize the agent
        try:
            agent = ResearchGPT(output_dir=output_dir, headless=True)
            print("Successfully initialized ResearchGPT agent")
        except Exception as agent_error:
            error_message = f"Error initializing ResearchGPT agent: {str(agent_error)}"
            print(error_message)
            print(traceback.format_exc())
            research_tasks[task_id]["status"] = "error"
            research_tasks[task_id]["error"] = error_message
            research_tasks[task_id]["traceback"] = traceback.format_exc()
            research_tasks[task_id]["status_details"] = error_message
            return
        
        # Track progress (simplified for now)
        def progress_callback(step, total_steps, message, progress):
            print(f"Progress update - Step {step}/{total_steps}: {message} ({progress:.0%})")
            research_tasks[task_id]["progress"] = progress
            research_tasks[task_id]["current_step"] = step
            research_tasks[task_id]["message"] = message
            research_tasks[task_id]["status_details"] = f"Step {step}/{total_steps}: {message}"
        
        # Conduct research - no longer passing subtopics
        try:
            research_tasks[task_id]["status_details"] = "Conducting research..."
            print(f"Conducting research for task {task_id}...")
            
            # Simply call conduct_research without subtopics
            result = agent.conduct_research(query, callback=progress_callback)
            
            # Validate result to ensure it has all required fields (without subtopics)
            required_fields = ["query", "md_path", "pdf_path", "summary", "stats"]
            missing_fields = [field for field in required_fields if field not in result]
            
            if missing_fields:
                raise ValueError(f"Research result missing required fields: {missing_fields}")
                
            # Ensure the report files exist
            if "md_path" in result and not os.path.exists(result["md_path"]):
                print(f"Warning: MD file not found at {result['md_path']}")
                
            if "pdf_path" in result and not os.path.exists(result["pdf_path"]):
                print(f"Warning: PDF file not found at {result['pdf_path']}")
            
            # If there are subtopics in the result, remove them to ensure they don't appear
            if "subtopics" in result:
                del result["subtopics"]
                
            # Update task with results
            print(f"Research completed for task {task_id}, updating results")
            research_tasks[task_id]["status"] = "completed"
            research_tasks[task_id]["result"] = result
            research_tasks[task_id]["completion_time"] = datetime.now().isoformat()
            research_tasks[task_id]["status_details"] = "Research completed successfully"
            print(f"Task {task_id} completed successfully")
            
        except Exception as research_error:
            error_message = f"Error during research: {str(research_error)}"
            print(error_message)
            traceback_str = traceback.format_exc()
            print(traceback_str)
            research_tasks[task_id]["status"] = "error"
            research_tasks[task_id]["error"] = error_message
            research_tasks[task_id]["traceback"] = traceback_str
            research_tasks[task_id]["status_details"] = error_message
        
    except Exception as e:
        error_message = f"Error in research task: {str(e)}"
        print(error_message)
        traceback_str = traceback.format_exc()
        print(traceback_str)
        
        research_tasks[task_id]["status"] = "error"
        research_tasks[task_id]["error"] = str(e)
        research_tasks[task_id]["traceback"] = traceback_str
        research_tasks[task_id]["status_details"] = error_message
        print(f"Task {task_id} failed with error: {str(e)}")

def test_task(task_id: str):
    """A simple test task to verify background processing."""
    try:
        print(f"Starting test task {task_id}")
        research_tasks[task_id]["status_details"] = "Test task started"
        
        # Simulate work with a few steps
        for i in range(1, 6):
            print(f"Test task {task_id} - step {i}/5")
            research_tasks[task_id]["progress"] = i / 5
            research_tasks[task_id]["current_step"] = i
            research_tasks[task_id]["status_details"] = f"Test step {i}/5"
            time.sleep(2)  # Sleep for 2 seconds to simulate work
            
        # Mark as completed - removed subtopics from result
        print(f"Test task {task_id} completed")
        research_tasks[task_id]["status"] = "completed"
        research_tasks[task_id]["result"] = {
            "query": "Test query",
            "summary": "This was a test task that completed successfully.",
            "stats": "Test stats",
            "md_path": "test_path.md",
            "pdf_path": "test_path.pdf"
        }
        research_tasks[task_id]["completion_time"] = datetime.now().isoformat()
        research_tasks[task_id]["status_details"] = "Test completed successfully"
        
    except Exception as e:
        print(f"Test task {task_id} failed: {str(e)}")
        research_tasks[task_id]["status"] = "error"
        research_tasks[task_id]["error"] = f"Test failed: {str(e)}"