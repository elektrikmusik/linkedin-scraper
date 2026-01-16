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
import json
import logging
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from playwright.async_api import Page

from linkedin_scraper.core.browser import BrowserManager
from linkedin_scraper.scrapers.base import BaseScraper
from linkedin_scraper.callbacks import ProgressCallback, SilentCallback


class JobCollection(str, Enum):
    """Available LinkedIn job collection types."""
    # Core collections
    RECOMMENDED = "recommended"  # For you
    TOP_APPLICANT = "top-applicant"  # Top Applicant
    EASY_APPLY = "easy-apply"
    HYBRID = "hybrid"
    REMOTE = "remote-jobs"
    PART_TIME = "part-time-jobs"
    
    # Industry sectors
    SUSTAINABILITY = "sustainability"
    MANUFACTURING = "manufacturing"
    DEFENSE_AND_SPACE = "defense-and-space"
    SOCIAL_IMPACT = "social-impact"
    GOVERNMENT = "government"
    PHARMACEUTICALS = "pharmaceuticals"  # Pharma
    BIOTECHNOLOGY = "biotechnology"  # Biotech
    CONSTRUCTION = "construction"
    REAL_ESTATE = "real-estate"
    RESTAURANTS = "restaurants"
    RETAIL = "retail"
    HOSPITALITY = "hospitality"
    FINANCIAL_SERVICES = "financial-services"  # Finance
    TRANSPORTATION_AND_LOGISTICS = "transportation-and-logistics"  # Logistics
    HOSPITALS_AND_HEALTHCARE = "hospitals-and-healthcare"  # Healthcare
    FOOD_AND_BEVERAGES = "food-and-beverages"  # Food & bev
    APPAREL_AND_FASHION = "apparel-and-fashion"  # Fashion
    MUSEUMS = "museums-historical-sites-and-zoos"  # Museums
    MEDIA = "media"
    PUBLISHING = "publishing"
    DIGITAL_SECURITY = "digital-security"
    
    # Professional fields
    HUMAN_RESOURCES = "human-resources"  # HR
    STAFFING_AND_RECRUITING = "staffing-and-recruiting"  # Recruiting
    MARKETING_AND_ADVERTISING = "marketing-and-advertising"  # Marketing
    CIVIL_ENGINEERING = "civil-eng"  # Civil eng
    
    # Education
    HIGHER_EDUCATION = "higher-edu"  # Higher ed
    EDUCATION = "education"
    
    # Other
    SMALL_BUSINESS = "small-business"  # Small biz
    VOLUNTEER = "volunteer"
    NON_PROFITS = "non-profits"  # Non-profit
    HUMAN_SERVICES = "human-services"
    CAREER_GROWTH = "career-growth"
    WORK_LIFE_BALANCE = "work-life-balance"
    
    @classmethod
    def choices(cls) -> List[str]:
        """Return list of valid collection choices."""
        return [c.value for c in cls]
    
    @classmethod
    def from_string(cls, value: str) -> "JobCollection":
        """Convert string to JobCollection enum."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(
                f"Invalid collection: '{value}'. "
                f"Valid choices: {', '.join(cls.choices())}"
            )

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class HiringTeamMember:
    """Data class for a hiring team member."""
    name: str
    profile_url: Optional[str] = None
    title: Optional[str] = None
    connection_degree: Optional[str] = None  # e.g., "2nd", "3rd"
    is_job_poster: bool = False
    mutual_connections: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class JobListing:
    """Data class for a job listing from a collection."""
    job_id: str
    job_url: str
    collection: str  # Which collection this job came from
    title: Optional[str] = None
    company: Optional[str] = None
    company_url: Optional[str] = None
    location: Optional[str] = None
    posted_time: Optional[str] = None
    employment_type: Optional[str] = None
    workplace_type: Optional[str] = None
    promoted: bool = False
    easy_apply: bool = False
    actively_hiring: bool = False  # "Actively reviewing applicants"
    description: Optional[str] = None  # Job description text
    hiring_team: Optional[List[Dict[str, Any]]] = None  # List of hiring team members
    match_analysis: Optional[Dict[str, Any]] = None  # Premium AI match analysis
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self, **kwargs) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), **kwargs)


class JobCollectionScraper(BaseScraper):
    """
    Scraper for LinkedIn Job Collections.
    
    This scraper navigates to various job collection pages and extracts 
    job listing information. Supports multiple collection types:
    - recommended: Personalized job recommendations
    - sustainability: Jobs in sustainability sector
    - manufacturing: Manufacturing industry jobs
    - defense-and-space: Defense & Space industry jobs
    - easy-apply: Jobs with Easy Apply enabled
    - hybrid: Hybrid work arrangement jobs
    - social-impact: Social impact focused jobs
    
    Example:
        async with BrowserManager(headless=False) as browser:
            await browser.load_session("linkedin_session.json")
            scraper = JobCollectionScraper(browser.page, collection=JobCollection.RECOMMENDED)
            jobs = await scraper.scrape(limit=25)
            for job in jobs:
                print(job.to_json(indent=2))
    """
    
    BASE_URL = "https://www.linkedin.com/jobs/collections/"
    
    def __init__(
        self, 
        page: Page, 
        collection: JobCollection = JobCollection.RECOMMENDED,
        callback: Optional[ProgressCallback] = None
    ):
        """
        Initialize job collection scraper.
        
        Args:
            page: Playwright page object
            collection: Job collection type to scrape
            callback: Optional progress callback
        """
        super().__init__(page, callback or SilentCallback())
        self.collection = collection
        self.collection_url = f"{self.BASE_URL}{collection.value}/"
    
    async def scrape(self, limit: int = 25, max_pages: int = 5, fetch_details: bool = False) -> List[JobListing]:
        """
        Scrape jobs from the specified LinkedIn collection.
        
        Args:
            limit: Maximum number of jobs to scrape
            max_pages: Maximum number of pages to scrape (for pagination)
            fetch_details: If True, click on each job to get description and hiring team
            
        Returns:
            List of JobListing objects
        """
        logger.info(f"Starting '{self.collection.value}' jobs scraping (limit={limit}, details={fetch_details})")
        await self.callback.on_start(f"JobCollection:{self.collection.value}", self.collection_url)
        
        all_jobs = []
        seen_job_ids = set()
        current_page = 1
        
        # Navigate to collection page
        await self.navigate_and_wait(self.collection_url)
        await self.callback.on_progress(f"Navigated to {self.collection.value} jobs page", 10)
        
        while len(all_jobs) < limit and current_page <= max_pages:
            logger.info(f"Processing page {current_page}...")
            
            # Wait for the job listings container to load
            await self._wait_for_jobs_list()
            
            # Scroll to load all jobs on current page
            jobs_on_page = await self._scroll_and_extract_all_jobs(limit - len(all_jobs), seen_job_ids)
            
            if not jobs_on_page:
                logger.info("No more jobs found on this page")
                break
            
            # If fetch_details is enabled, click on each job to get details
            if fetch_details:
                logger.info(f"Fetching details for {len(jobs_on_page)} jobs...")
                for i, job in enumerate(jobs_on_page):
                    try:
                        logger.debug(f"Fetching details for job {i+1}/{len(jobs_on_page)}: {job.job_id}")
                        details = await self._fetch_job_details(job.job_id)
                        if details:
                            job.description = details.get('description')
                            job.hiring_team = details.get('hiring_team')
                            job.match_analysis = details.get('match_analysis')
                    except Exception as e:
                        logger.debug(f"Error fetching details for job {job.job_id}: {e}")
            
            all_jobs.extend(jobs_on_page)
            for job in jobs_on_page:
                seen_job_ids.add(job.job_id)
            
            logger.info(f"Page {current_page}: Found {len(jobs_on_page)} jobs. Total: {len(all_jobs)}")
            await self.callback.on_progress(f"Page {current_page}: {len(all_jobs)} jobs collected", 
                                            min(90, 20 + (current_page * 15)))
            
            # Check if we have enough jobs
            if len(all_jobs) >= limit:
                break
            
            # Try to go to next page
            has_next = await self._go_to_next_page()
            if not has_next:
                logger.info("No more pages available")
                break
            
            current_page += 1
            await self.wait_and_focus(2)
        
        # Trim to limit
        all_jobs = all_jobs[:limit]
        
        await self.callback.on_progress("Scraping complete", 100)
        await self.callback.on_complete(f"JobCollection:{self.collection.value}", all_jobs)
        
        logger.info(f"Successfully scraped {len(all_jobs)} {self.collection.value} jobs from {current_page} page(s)")
        return all_jobs
    
    async def _scroll_and_extract_all_jobs(
        self, 
        limit: int, 
        seen_job_ids: set
    ) -> List[JobListing]:
        """
        Scroll through the job list and extract all visible jobs.
        LinkedIn shows ~25 jobs per page but loads them lazily.
        
        Args:
            limit: Maximum number of jobs to extract
            seen_job_ids: Set of already seen job IDs to avoid duplicates
            
        Returns:
            List of JobListing objects
        """
        jobs = []
        last_job_count = 0
        no_new_jobs_count = 0
        max_no_new_jobs = 5  # Stop if no new jobs after 5 scroll attempts
        
        # First, scroll to load all jobs on the page
        await self._load_all_jobs_on_page()
        
        while len(jobs) < limit and no_new_jobs_count < max_no_new_jobs:
            # Extract current visible jobs
            new_jobs = await self._extract_jobs_from_page(limit, seen_job_ids)
            
            for job in new_jobs:
                if job.job_id not in seen_job_ids and len(jobs) < limit:
                    jobs.append(job)
                    seen_job_ids.add(job.job_id)
            
            logger.debug(f"Extracted {len(jobs)} jobs so far...")
            
            # Check if we got new jobs
            if len(jobs) == last_job_count:
                no_new_jobs_count += 1
                # Try to load more by scrolling
                await self._fallback_scroll()
                await self.wait_and_focus(0.5)
            else:
                no_new_jobs_count = 0
            
            last_job_count = len(jobs)
            
            # Check if we have enough
            if len(jobs) >= limit:
                break
        
        return jobs
    
    async def _load_all_jobs_on_page(self) -> None:
        """
        Load all jobs on the current page by scrolling each list item into view.
        
        LinkedIn uses an 'occludable-update' mechanism where job cards are only 
        populated with data when scrolled into view. We need to scroll through
        each list item individually rather than jumping to the bottom.
        """
        try:
            # LinkedIn pre-loads 25 list item shells but only populates ~7 initially
            # We need to scroll each item into view to trigger data population
            
            await self.page.evaluate("""
                (async () => {
                    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
                    
                    // Find all list item shells
                    const items = document.querySelectorAll('.scaffold-layout__list-item');
                    
                    // Scroll each item into view to trigger lazy loading
                    for (let i = 0; i < items.length; i++) {
                        items[i].scrollIntoView({ behavior: 'instant', block: 'center' });
                        await sleep(150);  // Wait for occlusion mechanism to populate data
                    }
                    
                    // Scroll back to top
                    const container = document.querySelector('.scaffold-layout__list');
                    if (container) {
                        container.scrollTop = 0;
                    }
                })()
            """)
            
            # Wait for any remaining content to load
            await self.wait_and_focus(1)
            
            # Log how many jobs are now visible
            job_count = await self.page.locator('[data-job-id]').count()
            logger.info(f"Loaded {job_count} job cards on current page")
            
        except Exception as e:
            logger.warning(f"Error loading jobs on page: {e}")
            # Fallback: try simple scroll approach
            await self._fallback_scroll()
    
    async def _fallback_scroll(self) -> None:
        """Fallback scrolling method if the main approach fails."""
        try:
            for _ in range(5):
                await self.page.keyboard.press('End')
                await self.wait_and_focus(0.5)
        except Exception as e:
            logger.debug(f"Fallback scroll error: {e}")
    
    async def _go_to_next_page(self) -> bool:
        """
        Try to navigate to the next page of results.
        
        Returns:
            True if successfully navigated to next page, False otherwise
        """
        try:
            # Look for pagination controls
            next_button_selectors = [
                'button[aria-label="View next page"]',
                'button[aria-label="Next"]',
                '.artdeco-pagination__button--next',
                'li.artdeco-pagination__indicator--number.selected + li button',
                '[data-test-pagination-page-btn].artdeco-pagination__indicator--number.selected ~ li button',
            ]
            
            for selector in next_button_selectors:
                try:
                    next_btn = self.page.locator(selector).first
                    if await next_btn.count() > 0:
                        is_disabled = await next_btn.get_attribute('disabled')
                        if not is_disabled:
                            await next_btn.click()
                            await self.wait_and_focus(2)
                            return True
                except:
                    continue
            
            # Alternative: Look for "See more jobs" or pagination links
            see_more_selectors = [
                'button:has-text("See more jobs")',
                'button:has-text("Show more")',
                'a:has-text("See more jobs")',
            ]
            
            for selector in see_more_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if await btn.count() > 0:
                        await btn.click()
                        await self.wait_and_focus(2)
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error navigating to next page: {e}")
            return False
    
    async def _fetch_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Click on a job card to fetch its detailed information.
        
        Args:
            job_id: The job ID to fetch details for
            
        Returns:
            Dictionary with 'description', 'hiring_team', and 'match_analysis' keys, or None if failed
        """
        try:
            # Click on the job card to open its details
            job_card = self.page.locator(f'[data-job-id="{job_id}"]').first
            if await job_card.count() == 0:
                # Try to find by link
                job_card = self.page.locator(f'a[href*="/jobs/view/{job_id}"]').first
            
            if await job_card.count() > 0:
                await job_card.click()
                await self.wait_and_focus(3.0)  # Increased wait time for job details to load
                
                # Extract description
                description = await self._extract_job_description()
                
                # Extract hiring team
                hiring_team = await self._extract_hiring_team()
                
                # Try to extract match analysis (Premium feature)
                match_analysis = await self._extract_match_analysis()
                
                return {
                    'description': description,
                    'hiring_team': hiring_team,
                    'match_analysis': match_analysis
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error fetching job details: {e}")
            return None
    
    async def _extract_job_description(self) -> Optional[str]:
        """Extract the job description from the job details panel."""
        try:
            description_selectors = [
                '#job-details',
                '.jobs-description__content',
                '.jobs-description-content__text',
                '.jobs-box__html-content',
                'article.jobs-description__container',
            ]
            
            for selector in description_selectors:
                try:
                    desc_elem = self.page.locator(selector).first
                    if await desc_elem.count() > 0:
                        # Get text content, which strips HTML
                        description = await desc_elem.inner_text()
                        if description:
                            # Clean up the description
                            description = description.strip()
                            # Remove "About the job" header if present
                            if description.startswith('About the job'):
                                description = description[len('About the job'):].strip()
                            return description
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting job description: {e}")
            return None
    
    async def _extract_hiring_team(self) -> Optional[List[Dict[str, Any]]]:
        """Extract the hiring team information from the job details panel."""
        try:
            hiring_team = []
            
            # Look for the hiring team section
            hiring_section_selectors = [
                '.job-details-people-who-can-help__section',
                '.hirer-card__hirer-information',
                '[class*="hiring-team"]',
            ]
            
            # Try to find hiring team members
            for section_selector in hiring_section_selectors:
                sections = await self.page.locator(section_selector).all()
                if sections:
                    break
            
            # Look for individual hirer cards
            hirer_cards = await self.page.locator('.hirer-card__hirer-information, .job-details-people-who-can-help__section .display-flex.align-items-center').all()
            
            for card in hirer_cards:
                try:
                    member = {}
                    
                    # Extract name
                    name_elem = card.locator('.jobs-poster__name strong, [class*="name"] strong').first
                    if await name_elem.count() > 0:
                        member['name'] = (await name_elem.inner_text()).strip()
                    else:
                        # Try to get name from link
                        name_link = card.locator('a[href*="/in/"]').first
                        if await name_link.count() > 0:
                            name_text = await name_link.inner_text()
                            if name_text:
                                member['name'] = name_text.strip().split('\n')[0]
                    
                    if not member.get('name'):
                        continue
                    
                    # Extract profile URL
                    profile_link = card.locator('a[href*="/in/"]').first
                    if await profile_link.count() > 0:
                        href = await profile_link.get_attribute('href')
                        if href:
                            if not href.startswith('http'):
                                href = f"https://www.linkedin.com{href}"
                            member['profile_url'] = href.split('?')[0]  # Remove query params
                    
                    # Extract title
                    title_selectors = [
                        '.linked-area .text-body-small',
                        '.hirer-card__job-poster',
                        '[class*="subtitle"]',
                    ]
                    for title_selector in title_selectors:
                        title_elem = card.locator(title_selector).first
                        if await title_elem.count() > 0:
                            title_text = await title_elem.inner_text()
                            if title_text and 'Job poster' not in title_text:
                                member['title'] = title_text.strip()
                                break
                    
                    # Extract connection degree
                    degree_elem = card.locator('.hirer-card__connection-degree, [class*="connection-degree"]').first
                    if await degree_elem.count() > 0:
                        member['connection_degree'] = (await degree_elem.inner_text()).strip()
                    
                    # Check if job poster
                    card_text = await card.inner_text()
                    member['is_job_poster'] = 'job poster' in card_text.lower()
                    
                    # Extract mutual connections
                    if 'mutual connection' in card_text.lower():
                        # Try to parse "X mutual connections"
                        import re
                        match = re.search(r'(\d+)\s*mutual\s*connection', card_text.lower())
                        if match:
                            member['mutual_connections'] = match.group(1)
                    
                    hiring_team.append(member)
                    
                except Exception as e:
                    logger.debug(f"Error parsing hirer card: {e}")
                    continue
            
            return hiring_team if hiring_team else None
            
        except Exception as e:
            logger.debug(f"Error extracting hiring team: {e}")
            return None
    
    async def _extract_match_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Extract the Premium AI match analysis by clicking 'Show match details'.
        
        This is a Premium feature that provides AI-generated analysis of how
        well your profile matches the job requirements.
        """
        try:
            # Look for "Show match details" button - try for a few seconds as it might load late
            match_btn_selectors = [
                'button[aria-label="Show match details"]',
                'button:has-text("Show match details")',
                'a:has-text("Show match details")',
                'a[aria-label="Show match details"]',
                '.coach-shared-hscroll-button__action--guide-prompt',
            ]
            
            show_button = None
            # Poll for button up to 3 seconds
            for _ in range(6):  # 6 * 0.5s = 3s
                for selector in match_btn_selectors:
                    try:
                        btn = self.page.locator(selector).first
                        if await btn.count() > 0:
                            if await btn.is_visible():
                                show_button = btn
                                break
                    except:
                        continue
                if show_button:
                    break
                await asyncio.sleep(0.5)
            
            if not show_button:
                logger.debug("Match details button not found")
                return None
            
            # Click the button to show match details
            logger.debug("Clicking match details button...")
            await show_button.click()
            await self.wait_and_focus(4.0)  # Wait longer for analysis to load
            
            # Wait for the match analysis to appear
            analysis_selectors = [
                '.coach-message-ai-response',
                '.coach-message__text',
                '[data-coach-message-item]',
                '.coach-message-list__scroller',
            ]
            
            analysis_elem = None
            for selector in analysis_selectors:
                try:
                    elem = self.page.locator(selector).first
                    if await elem.count() > 0:
                        analysis_elem = elem
                        logger.debug(f"Found analysis element with selector: {selector}")
                        break
                except:
                    continue
            
            if not analysis_elem:
                logger.debug("Match analysis element not found after click")
                return None
            
            # Extract the analysis text
            analysis_text = await analysis_elem.inner_text()
            
            if not analysis_text:
                return None
            
            # Parse the analysis
            import re
            
            result = {
                'raw_text': analysis_text.strip(),
                'summary': None,
                'matched_qualifications': [],
                'missing_qualifications': [],
                'total_required': None,
                'total_matched': None,
            }
            
            # Extract summary line (e.g., "You'd be a top applicant")
            lines = analysis_text.split('\n')
            for line in lines:
                line = line.strip()
                if 'top applicant' in line.lower() or 'strong match' in line.lower() or 'good match' in line.lower():
                    result['summary'] = line
                    break
                elif line and not line.startswith('✓') and not line.startswith('?') and not 'qualification' in line.lower():
                    # First substantive line is likely the summary
                    if not result['summary']:
                        result['summary'] = line
            
            # Extract qualification counts (e.g., "Matches 2 of the 5 required qualifications")
            match_count = re.search(r'matches?\s+(\d+)\s+of\s+(?:the\s+)?(\d+)\s+required', analysis_text.lower())
            if match_count:
                result['total_matched'] = int(match_count.group(1))
                result['total_required'] = int(match_count.group(2))
            
            # Extract matched qualifications (✓)
            for line in lines:
                line = line.strip()
                if line.startswith('✓'):
                    qual = line[1:].strip()
                    if qual:
                        result['matched_qualifications'].append(qual)
            
            # Extract missing/uncertain qualifications (?)
            for line in lines:
                line = line.strip()
                if line.startswith('?'):
                    qual = line[1:].strip()
                    if qual:
                        result['missing_qualifications'].append(qual)
            
            return result
            
        except Exception as e:
            logger.debug(f"Error extracting match analysis: {e}")
            return None
    
    async def _extract_jobs_from_page(
        self, 
        limit: int, 
        seen_job_ids: set
    ) -> List[JobListing]:
        """
        Extract job listings from the current page state.
        
        Args:
            limit: Maximum number of jobs to extract
            seen_job_ids: Set of already seen job IDs
            
        Returns:
            List of JobListing objects
        """
        jobs = []
        
        try:
            # Find all job cards - try multiple selector patterns
            job_card_selectors = [
                '[data-job-id]',
                '.job-card-container',
                '.jobs-job-board-list__item',
                '.scaffold-layout__list-item',
                'li.ember-view.occludable-update',
            ]
            
            job_cards = []
            for selector in job_card_selectors:
                try:
                    cards = await self.page.locator(selector).all()
                    if cards and len(cards) > 0:
                        job_cards = cards
                        logger.debug(f"Found {len(cards)} job cards with selector: {selector}")
                        break
                except:
                    continue
            
            if not job_cards:
                return jobs
            
            for card in job_cards:
                if len(jobs) >= limit:
                    break
                
                try:
                    job = await self._parse_job_card(card)
                    if job and job.job_id not in seen_job_ids:
                        jobs.append(job)
                except Exception as e:
                    logger.debug(f"Error parsing job card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting jobs: {e}")
        
        return jobs
    
    async def _wait_for_jobs_list(self, timeout: int = 15000) -> None:
        """Wait for the jobs list container to appear."""
        try:
            # Try multiple possible selectors for the jobs container
            selectors = [
                '.scaffold-layout__list-container',
                '.jobs-search-results-list',
                '[data-job-id]',
                '.job-card-container',
                '.jobs-job-board-list__item'
            ]
            
            for selector in selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=timeout // len(selectors))
                    logger.debug(f"Found jobs container with selector: {selector}")
                    return
                except:
                    continue
            
            # If none of the selectors work, wait a bit and continue anyway
            logger.warning("Could not find specific job container, continuing anyway...")
            await self.wait_and_focus(2)
            
        except Exception as e:
            logger.warning(f"Error waiting for jobs list: {e}")
            await self.wait_and_focus(3)
    
    async def _parse_job_card(self, card) -> Optional[JobListing]:
        """
        Parse a single job card element.
        
        Args:
            card: Playwright locator for the job card
            
        Returns:
            JobListing object or None if parsing fails
        """
        try:
            # Extract job ID
            job_id = await card.get_attribute('data-job-id')
            if not job_id:
                # Try to find job ID from a child element or link
                try:
                    link = card.locator('a[href*="/jobs/view/"]').first
                    href = await link.get_attribute('href')
                    if href:
                        # Extract job ID from URL like /jobs/view/1234567890/
                        parts = href.split('/jobs/view/')
                        if len(parts) > 1:
                            job_id = parts[1].split('/')[0].split('?')[0]
                except:
                    pass
            
            if not job_id:
                return None
            
            # Build job URL
            job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            
            # Extract job title
            title = None
            title_selectors = [
                '.job-card-list__title',
                '.artdeco-entity-lockup__title',
                'a[class*="job-card"] strong',
                '.job-card-container__link strong',
                'strong',
                '[class*="title"]'
            ]
            for selector in title_selectors:
                try:
                    title_elem = card.locator(selector).first
                    if await title_elem.count() > 0:
                        title = await title_elem.inner_text()
                        title = title.strip() if title else None
                        if title:
                            break
                except:
                    continue
            
            # Extract company name
            company = None
            company_selectors = [
                '.job-card-container__primary-description',
                '.artdeco-entity-lockup__subtitle',
                '.job-card-container__company-name',
                '[class*="company"]',
                '.job-card-list__company-name'
            ]
            for selector in company_selectors:
                try:
                    company_elem = card.locator(selector).first
                    if await company_elem.count() > 0:
                        company = await company_elem.inner_text()
                        company = company.strip() if company else None
                        if company:
                            break
                except:
                    continue
            
            # Extract location
            location = None
            location_selectors = [
                '.job-card-container__metadata-item',
                '.artdeco-entity-lockup__caption',
                '[class*="location"]',
                '.job-card-list__location'
            ]
            for selector in location_selectors:
                try:
                    location_elem = card.locator(selector).first
                    if await location_elem.count() > 0:
                        location = await location_elem.inner_text()
                        location = location.strip() if location else None
                        if location:
                            break
                except:
                    continue
            
            # Extract posted time
            posted_time = None
            try:
                time_elem = card.locator('time').first
                if await time_elem.count() > 0:
                    posted_time = await time_elem.inner_text()
                    posted_time = posted_time.strip() if posted_time else None
            except:
                pass
            
            # Get full card text for badge detection
            card_text = ""
            try:
                card_text = await card.inner_text()
            except:
                pass
            
            # Check for Easy Apply badge - look for "Easy Apply" text in the card
            easy_apply = False
            try:
                # Method 1: Check if "Easy Apply" text exists in card
                if 'easy apply' in card_text.lower():
                    easy_apply = True
                else:
                    # Method 2: Look for Easy Apply specific elements
                    easy_apply_selectors = [
                        'span:has-text("Easy Apply")',
                        '[class*="easy-apply"]',
                        '[aria-label*="Easy Apply"]',
                        '.job-card-container__apply-method'
                    ]
                    for selector in easy_apply_selectors:
                        try:
                            elem = card.locator(selector).first
                            if await elem.count() > 0:
                                easy_apply = True
                                break
                        except:
                            continue
            except:
                pass
            
            # Check if promoted
            promoted = 'promoted' in card_text.lower()
            
            # Extract company URL
            company_url = None
            try:
                company_links = card.locator('a[href*="/company/"]')
                if await company_links.count() > 0:
                    company_url = await company_links.first.get_attribute('href')
                    if company_url and not company_url.startswith('http'):
                        company_url = f"https://www.linkedin.com{company_url}"
            except:
                pass
            
            # Extract employment type and workplace type from metadata
            employment_type = None
            workplace_type = None
            try:
                metadata_items = await card.locator('.job-card-container__metadata-item, .artdeco-entity-lockup__metadata').all()
                for item in metadata_items:
                    text = await item.inner_text()
                    text_lower = text.lower().strip()
                    if any(t in text_lower for t in ['full-time', 'part-time', 'contract', 'internship', 'temporary']):
                        employment_type = text.strip()
                    elif any(t in text_lower for t in ['remote', 'on-site', 'hybrid']):
                        workplace_type = text.strip()
            except:
                pass
            
            # Check for "Actively reviewing applicants" status
            actively_hiring = False
            try:
                if 'actively reviewing' in card_text.lower():
                    actively_hiring = True
                else:
                    # Try to find the specific insight element
                    insight_elem = card.locator('.job-card-container__job-insight-text').first
                    if await insight_elem.count() > 0:
                        insight_text = await insight_elem.inner_text()
                        if 'actively reviewing' in insight_text.lower():
                            actively_hiring = True
            except:
                pass
            
            return JobListing(
                job_id=job_id,
                job_url=job_url,
                collection=self.collection.value,
                title=title,
                company=company,
                company_url=company_url,
                location=location,
                posted_time=posted_time,
                employment_type=employment_type,
                workplace_type=workplace_type,
                promoted=promoted,
                easy_apply=easy_apply,
                actively_hiring=actively_hiring,
            )
            
        except Exception as e:
            logger.debug(f"Error parsing job card: {e}")
            return None


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Scrape LinkedIn Job Collections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scrape_recommended_jobs.py                    # Default: recommended jobs
  python scrape_recommended_jobs.py -c easy-apply      # Easy Apply jobs
  python scrape_recommended_jobs.py -c hybrid -l 50    # 50 hybrid jobs
  python scrape_recommended_jobs.py -c remote-jobs     # Remote jobs
  python scrape_recommended_jobs.py --collection sustainability --headless

Available collections (39 total):

  CORE:
    recommended, top-applicant, easy-apply, hybrid, remote-jobs, part-time-jobs

  INDUSTRIES:
    sustainability, manufacturing, defense-and-space, social-impact,
    government, pharmaceuticals, biotechnology, construction,
    real-estate, restaurants, retail, hospitality, financial-services,
    transportation-and-logistics, hospitals-and-healthcare,
    food-and-beverages, apparel-and-fashion, museums-historical-sites-and-zoos,
    media, publishing, digital-security

  PROFESSIONAL:
    human-resources, staffing-and-recruiting, marketing-and-advertising, civil-eng

  EDUCATION:
    higher-edu, education

  OTHER:
    small-business, volunteer, non-profits, human-services,
    career-growth, work-life-balance
        """
    )
    
    parser.add_argument(
        "-c", "--collection",
        type=str,
        default="recommended",
        choices=JobCollection.choices(),
        help="Job collection to scrape (default: recommended)"
    )
    
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=25,
        help="Maximum number of jobs to scrape (default: 25)"
    )
    
    parser.add_argument(
        "-p", "--pages",
        type=int,
        default=5,
        help="Maximum number of pages to scrape (default: 5)"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: False)"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: {collection}_jobs.json)"
    )
    
    parser.add_argument(
        "--session",
        type=str,
        default="linkedin_session.json",
        help="Path to LinkedIn session file (default: linkedin_session.json)"
    )
    
    parser.add_argument(
        "-d", "--details",
        action="store_true",
        help="Fetch full job description and hiring team for each job (slower)"
    )
    
    return parser.parse_args()


async def main():
    """Scrape job collection from LinkedIn."""
    args = parse_args()
    
    # Parse collection
    collection = JobCollection.from_string(args.collection)
    
    print("=" * 60)
    print(f"LinkedIn Job Collection Scraper: {collection.value.upper()}")
    print("=" * 60)
    print(f"Collection: {collection.value}")
    print(f"Limit:      {args.limit}")
    print(f"Max Pages:  {args.pages}")
    print(f"Details:    {args.details}")
    print(f"Headless:   {args.headless}")
    print("=" * 60)
    
    # Initialize browser
    async with BrowserManager(headless=args.headless) as browser:
        # Load existing session
        try:
            await browser.load_session(args.session)
            print("✓ Session loaded")
        except FileNotFoundError:
            print(f"✗ Session file not found: {args.session}")
            print("  Please run 'python samples/create_session.py' first to log in.")
            return
        
        # Initialize scraper with collection
        scraper = JobCollectionScraper(browser.page, collection=collection)
        
        # Scrape jobs
        details_note = " (with details)" if args.details else ""
        print(f"\n🚀 Scraping {collection.value} jobs{details_note} (up to {args.limit} jobs, max {args.pages} pages)...")
        jobs = await scraper.scrape(limit=args.limit, max_pages=args.pages, fetch_details=args.details)
        
        # Display results
        print("\n" + "=" * 60)
        print(f"📋 Found {len(jobs)} {collection.value.replace('-', ' ').title()} Jobs")
        print("=" * 60)
        
        for i, job in enumerate(jobs, 1):
            print(f"\n--- Job #{i} ---")
            print(f"Title:     {job.title or 'N/A'}")
            print(f"Company:   {job.company or 'N/A'}")
            print(f"Location:  {job.location or 'N/A'}")
            print(f"Posted:    {job.posted_time or 'N/A'}")
            if job.employment_type:
                print(f"Type:      {job.employment_type}")
            if job.workplace_type:
                print(f"Workplace: {job.workplace_type}")
            if job.easy_apply:
                print("Easy Apply: ✓")
            if job.actively_hiring:
                print("Actively Hiring: ✓")
            if job.promoted:
                print("Promoted:  ✓")
            if job.match_analysis:
                summary = job.match_analysis.get('summary', '')
                matched = job.match_analysis.get('total_matched')
                total = job.match_analysis.get('total_required')
                if summary:
                    print(f"Match: {summary}")
                if matched is not None and total is not None:
                    print(f"  Qualifications: {matched}/{total} matched")
                    for qual in job.match_analysis.get('matched_qualifications', [])[:2]:
                        print(f"    ✓ {qual[:60]}{'...' if len(qual) > 60 else ''}")
                    for qual in job.match_analysis.get('missing_qualifications', [])[:2]:
                        print(f"    ? {qual[:60]}{'...' if len(qual) > 60 else ''}")
            if job.hiring_team:
                print(f"Hiring Team: {len(job.hiring_team)} member(s)")
                for member in job.hiring_team[:2]:  # Show first 2
                    name = member.get('name', 'Unknown')
                    title = member.get('title', '')
                    degree = member.get('connection_degree', '')
                    print(f"  - {name}{' (' + title + ')' if title else ''}{' [' + degree + ']' if degree else ''}")
            if job.description:
                desc_preview = job.description[:150].replace('\n', ' ')
                if len(job.description) > 150:
                    desc_preview += "..."
                print(f"Description: {desc_preview}")
            print(f"URL:       {job.job_url}")
        
        # Save to JSON file
        output_file = args.output or f"{collection.value}_jobs.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump([job.to_dict() for job in jobs], f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to {output_file}")
    
    print("\n✓ Done!")


if __name__ == "__main__":
    asyncio.run(main())
