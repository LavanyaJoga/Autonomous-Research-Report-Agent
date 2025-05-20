from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

class SourceSummary(BaseModel):
    source: str
    summary: str

class ReportInput(BaseModel):
    topic: str
    mainSummary: str
    sources: List[SourceSummary]
    subtopics: List[str] = []

@router.post("/generate-report")
async def generate_report(input_data: ReportInput):
    """Generate a comprehensive report based on summaries."""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Create prompt using the provided data
        sources_text = "\n\n".join([
            f"Source: {source.source}\nSummary: {source.summary}"
            for source in input_data.sources
        ])
        
        subtopics_text = "\n".join([
            f"- {subtopic}" for subtopic in input_data.subtopics
        ])
        
        prompt = f"""
        Create a comprehensive research report on "{input_data.topic}" using the following information:
        
        Main Summary:
        {input_data.mainSummary}
        
        Subtopics to cover:
        {subtopics_text}
        
        Source Summaries:
        {sources_text}
        
        Your task is to:
        1. Generate an executive summary
        2. Create sections for each subtopic, incorporating relevant information from the sources
        3. Ensure the report is factual, well-structured, and comprehensive
        4. Format the report using Markdown with appropriate headings and formatting
        
        Return only the report in Markdown format.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert research report writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=2500
        )
        
        report_content = response.choices[0].message.content.strip()
        
        return {
            "report": report_content,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")
