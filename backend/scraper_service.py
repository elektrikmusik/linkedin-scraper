import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Optional

from linkedin_scraper.core.browser import BrowserManager
from linkedin_scraper.scrapers.recommended_jobs import JobCollectionScraper, JobCollection
from linkedin_scraper.callbacks import ProgressCallback
from linkedin_scraper.models.job import RecommendedJob

from backend.schemas import ScrapeStatus
from backend.database import db

logger = logging.getLogger(__name__)

# In-memory storage for job statuses (replace with Redis/DB for production)
job_store: Dict[str, ScrapeStatus] = {}

class ServiceCallback(ProgressCallback):
    """Callback to update job status."""
    def __init__(self, task_id: str):
        self.task_id = task_id
    
    async def on_start(self, scraper_type: str, url: str):
        if self.task_id in job_store:
            job_store[self.task_id].message = f"Starting {scraper_type}..."
            job_store[self.task_id].status = "running"
    
    async def on_progress(self, message: str, percent: int):
        if self.task_id in job_store:
            job_store[self.task_id].message = message
            job_store[self.task_id].progress = percent
            job_store[self.task_id].updated_at = datetime.now().isoformat()
    
    async def on_complete(self, scraper_type: str, result: list):
        # Result handling is done in main function
        pass
    
    async def on_error(self, error: Exception):
        if self.task_id in job_store:
            job_store[self.task_id].error = str(error)

async def run_scrape_task(
    task_id: str,
    collection: str,
    limit: int = 10,
    pages: int = 1,
    details: bool = False,
    owner_id: Optional[str] = None
):
    """
    Background task to run the scraping process.
    """
    try:
        # Initialize status
        job_store[task_id] = ScrapeStatus(
            id=task_id,
            status="starting",
            collection=collection,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        logger.info(f"Starting scrape task {task_id} for collection {collection}")
        
        async with BrowserManager(headless=False) as browser: # Headless=False for now to avoid detection
            # Load session
            try:
                await browser.load_session("linkedin_session.json")
            except Exception as e:
                logger.warning(f"Could not load session: {e}")
                # We might want to fail here if login is strictly required
            
            callback = ServiceCallback(task_id)
            
            scraper = JobCollectionScraper(
                browser.page,
                collection=collection,
                callback=callback
            )
            
            # Run scrape
            jobs = await scraper.scrape(limit=limit, max_pages=pages, fetch_details=details)
            
            # Update status
            job_store[task_id].jobs_collected = len(jobs)
            job_store[task_id].message = f"Saving {len(jobs)} jobs to database..."
            job_store[task_id].progress = 95
            
            # Save to DB
            success = db.upsert_jobs(jobs, owner_id=owner_id)
            
            # Finalize status
            job_store[task_id].status = "completed"
            job_store[task_id].progress = 100
            job_store[task_id].message = "Completed" if success else "Completed (DB save failed)"
            job_store[task_id].updated_at = datetime.now().isoformat()
            
    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        if task_id in job_store:
            job_store[task_id].status = "failed"
            job_store[task_id].error = str(e)
            job_store[task_id].updated_at = datetime.now().isoformat()

def get_job_status(task_id: str) -> Optional[ScrapeStatus]:
    return job_store.get(task_id)

def create_scrape_job(collection: str, limit: int, pages: int, details: bool, owner_id: Optional[str] = None) -> str:
    task_id = str(uuid.uuid4())
    # Initial status
    job_store[task_id] = ScrapeStatus(
        id=task_id,
        status="pending",
        collection=collection,
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat()
    )
    
    # Schedule background task
    asyncio.create_task(run_scrape_task(task_id, collection, limit, pages, details, owner_id))
    
    return task_id
