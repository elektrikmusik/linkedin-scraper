from pydantic import BaseModel, Field
from typing import Optional, List, Any

# Request Models
class ScrapeRequest(BaseModel):
    collection: str = Field(..., description="Job collection to scrape (e.g., 'top-applicant')")
    limit: int = Field(10, description="Max number of jobs to scrape")
    pages: int = Field(1, description="Max pages to traverse")
    details: bool = Field(False, description="Fetch full details including description and match analysis")
    owner_id: Optional[str] = Field(None, description="The user ID who owns these jobs")

# Response Models
class ScrapeResponse(BaseModel):
    job_id: str
    status: str
    message: str

class ScrapeStatus(BaseModel):
    id: str
    status: str  # pending, running, completed, failed
    collection: str
    progress: int = 0
    message: Optional[str] = None
    jobs_collected: int = 0
    error: Optional[str] = None
    created_at: str
    updated_at: str
