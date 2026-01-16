#!/usr/bin/env python3
"""
Example: Scrape LinkedIn Job Collections

This example shows how to scrape job collections from LinkedIn.
Supports multiple collection types including recommended, sustainability,
manufacturing, defense-and-space, easy-apply, hybrid, and social-impact.

URL: https://www.linkedin.com/jobs/collections/[COLLECTION]/
"""
import argparse
import asyncio
import logging
from typing import List

from linkedin_scraper.core.browser import BrowserManager
from linkedin_scraper.scrapers.recommended_jobs import JobCollectionScraper, JobCollection, RecommendedJob
from linkedin_scraper.callbacks import ProgressCallback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SampleCallback(ProgressCallback):
    """Callback to print progress to console."""
    async def on_start(self, scraper_type: str, url: str):
        print(f"🚀 Scraping {scraper_type}...")
        print(f"   URL: {url}")
    
    async def on_progress(self, message: str, percent: int):
        print(f"[{percent}%] {message}")
    
    async def on_complete(self, scraper_type: str, result: List[RecommendedJob]):
        print(f"✓ {scraper_type} complete! Found {len(result)} jobs.")
    
    async def on_error(self, error: Exception):
        print(f"✗ Error: {error}")


async def scrape_collection(
    collection_name: str, 
    limit: int = 25, 
    max_pages: int = 5,
    details: bool = False,
    headless: bool = False
):
    """Run the scraping job."""
    print("="*60)
    print(f"LinkedIn Job Collection Scraper: {collection_name.upper()}")
    print("="*60)
    print(f"Collection: {collection_name}")
    print(f"Limit:      {limit}")
    print(f"Max Pages:  {max_pages}")
    print(f"Details:    {details}")
    print(f"Headless:   {headless}")
    print("="*60)
    
    async with BrowserManager(headless=headless) as browser:
        # Load session if exists
        try:
            await browser.load_session("linkedin_session.json")
            print("✓ Session loaded")
        except:
            print("⚠ No session found, you may need to login manually")
        
        # Create callback
        callback = SampleCallback()
        
        # Initialize scraper
        scraper = JobCollectionScraper(
            browser.page, 
            collection=collection_name,
            callback=callback
        )
        
        # Run scraping
        jobs = await scraper.scrape(limit=limit, max_pages=max_pages, fetch_details=details)
        
        # Save results
        filename = f"{collection_name}_jobs.json"
        
        # Convert Pydantic models to dictionaries for saving
        jobs_data = [job.model_dump() for job in jobs]
        
        import json
        with open(filename, "w") as f:
            json.dump(jobs_data, f, indent=2, default=str)
        
        print("\n" + "="*60)
        print(f"📋 Found {len(jobs)} {collection_name.replace('-', ' ').title()} Jobs")
        print("="*60)
        
        for i, job in enumerate(jobs):
            print(f"\n--- Job #{i+1} ---")
            print(f"Title:     {job.title}")
            print(f"Company:   {job.company}")
            print(f"Location:  {job.location}")
            print(f"Posted:    {job.posted_time}")
            
            if job.match_analysis:
                # Handle Pydantic model object access
                summary = job.match_analysis.summary
                matched = job.match_analysis.total_matched
                total = job.match_analysis.total_required
                
                if summary:
                    print(f"Match: {summary}")
                
                if matched is not None and total is not None:
                    print(f"  Qualifications: {matched}/{total} matched")
                
                if job.match_analysis.matched_qualifications:
                    for qual in job.match_analysis.matched_qualifications[:2]:
                        print(f"    ✓ {qual[:60]}{'...' if len(qual) > 60 else ''}")
                        
                if job.match_analysis.missing_qualifications:
                    for qual in job.match_analysis.missing_qualifications[:2]:
                        print(f"    ? {qual[:60]}{'...' if len(qual) > 60 else ''}")
            
            if job.hiring_team:
                print(f"Hiring Team: {len(job.hiring_team)} member(s)")
                for member in job.hiring_team:
                    # Handle Pydantic model object access
                    print(f"  - {member.name} ({member.title}) [{member.connection_degree}]")
            
            print(f"URL:       {job.job_url}")
        
        print(f"\n💾 Results saved to {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape LinkedIn Job Collections")
    
    # Collection types
    parser.add_argument(
        "-c", "--collection", 
        type=str, 
        default="recommended",
        help=f"Collection type to scrape (default: recommended). Choices: {', '.join(JobCollection.choices())}"
    )
    
    parser.add_argument("-l", "--limit", type=int, default=25, help="Max jobs to scrape")
    parser.add_argument("-p", "--pages", type=int, default=1, help="Max pages to traverse")
    parser.add_argument("--details", action="store_true", help="Fetch full job details (description, hiring team)")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    
    args = parser.parse_args()
    
    asyncio.run(scrape_collection(
        args.collection, 
        limit=args.limit, 
        max_pages=args.pages,
        details=args.details,
        headless=args.headless
    ))
