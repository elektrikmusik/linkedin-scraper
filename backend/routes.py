from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List

from linkedin_scraper.scrapers.recommended_jobs import JobCollection

from backend.schemas import ScrapeRequest, ScrapeResponse, ScrapeStatus
from backend.scraper_service import create_scrape_job, get_job_status

router = APIRouter(prefix="/api")

@router.get("/collections", response_model=List[str])
async def get_collections():
    """List available job collections."""
    return JobCollection.choices()

@router.post("/scrape", response_model=ScrapeResponse)
async def trigger_scrape(request: ScrapeRequest):
    """
    Trigger a new scraping job.
    Returns a job_id to track progress.
    """
    # Validate collection
    if request.collection not in JobCollection.choices():
        raise HTTPException(status_code=400, detail=f"Invalid collection. Choices: {JobCollection.choices()}")
    
    task_id = create_scrape_job(
        collection=request.collection,
        limit=request.limit,
        pages=request.pages,
        details=request.details,
        owner_id=request.owner_id
    )
    
    return ScrapeResponse(
        job_id=task_id,
        status="pending",
        message="Scrape job started in background"
    )

@router.get("/jobs/{job_id}", response_model=ScrapeStatus)
async def get_job(job_id: str):
    """Get the status of a scraping job."""
    status = get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status
