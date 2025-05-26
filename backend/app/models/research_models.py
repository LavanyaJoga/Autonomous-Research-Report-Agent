from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=10, description="The research topic to investigate")
    timestamp: Optional[int] = None
    requestId: Optional[str] = None
    useDynamicSources: Optional[bool] = False

class ResearchResponse(BaseModel):
    task_id: str = Field(..., description="ID to track the research task")
    status: str = Field(..., description="Status of the research task")
    message: str = Field(..., description="Status message")

class ResearchResult(BaseModel):
    query: str = Field(..., description="The original research query")
    summary: str = Field(..., description="Summary of the research findings")
    stats: str = Field(..., description="Statistics about the research")
    subtopics: List[str] = Field(..., description="List of research subtopics")
    md_path: str = Field(..., description="Path to the markdown report")
    pdf_path: str = Field(..., description="Path to the PDF report")