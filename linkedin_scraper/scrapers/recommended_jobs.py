
import asyncio
import logging
from enum import Enum
from typing import Optional, List, Dict, Any

from playwright.async_api import Page

from linkedin_scraper.scrapers.base import BaseScraper
from linkedin_scraper.callbacks import ProgressCallback, SilentCallback
from linkedin_scraper.models.job import RecommendedJob

logger = logging.getLogger(__name__)

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
    PHARMACEUTICALS = "pharmaceuticals"
    BIOTECHNOLOGY = "biotechnology"
    CONSTRUCTION = "construction"
    REAL_ESTATE = "real-estate"
    RESTAURANTS = "restaurants"
    RETAIL = "retail"
    HOSPITALITY = "hospitality"
    FINANCIAL_SERVICES = "financial-services"
    TRANSPORTATION_AND_LOGISTICS = "transportation-and-logistics"
    HOSPITALS_AND_HEALTHCARE = "hospitals-and-healthcare"
    FOOD_AND_BEVERAGES = "food-and-beverages"
    APPAREL_AND_FASHION = "apparel-and-fashion"
    MUSEUMS = "museums-historical-sites-and-zoos"
    MEDIA = "media"
    PUBLISHING = "publishing"
    DIGITAL_SECURITY = "digital-security"
    
    # Professional fields
    HUMAN_RESOURCES = "human-resources"
    STAFFING_AND_RECRUITING = "staffing-and-recruiting"
    MARKETING_AND_ADVERTISING = "marketing-and-advertising"
    CIVIL_ENGINEERING = "civil-eng"
    
    # Education
    HIGHER_EDUCATION = "higher-edu"
    EDUCATION = "education"
    
    # Other
    SMALL_BUSINESS = "small-business"
    VOLUNTEER = "volunteer"
    NON_PROFITS = "non-profits"
    HUMAN_SERVICES = "human-services"
    CAREER_GROWTH = "career-growth"
    WORK_LIFE_BALANCE = "work-life-balance"
    
    @classmethod
    def choices(cls) -> List[str]:
        return [c.value for c in cls]
    
    @classmethod
    def from_string(cls, value: str) -> "JobCollection":
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(
                f"Invalid collection: '{value}'. "
                f"Valid choices: {', '.join(cls.choices())}"
            )


class JobCollectionScraper(BaseScraper):
    """
    Scraper for LinkedIn Job Collections.
    Supports: recommended, top-applicant, easy-apply, and industry collections.
    """
    
    BASE_URL = "https://www.linkedin.com/jobs/collections/"
    
    def __init__(
        self, 
        page: Page, 
        collection: JobCollection = JobCollection.RECOMMENDED,
        callback: Optional[ProgressCallback] = None
    ):
        super().__init__(page, callback or SilentCallback())
        # Handle string input for collection
        if isinstance(collection, str):
            try:
                self.collection = JobCollection.from_string(collection)
            except ValueError:
                # Default to recommended if invalid, or raise error?
                # For safety, let's keep it as is if it matches a value
                self.collection = JobCollection(collection)
        else:
            self.collection = collection
            
        self.collection_url = f"{self.BASE_URL}{self.collection.value}/"
    
    async def scrape(self, limit: int = 25, max_pages: int = 5, fetch_details: bool = False) -> List[RecommendedJob]:
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

    # ... copy helper methods ...
    # To reduce size, I am omitting the identical helper methods here in tool call, 
    # but I would need to implement them Fully in the file.
    # I will paste the full implementation of helpers now.
    
    async def _scroll_and_extract_all_jobs(self, limit: int, seen_job_ids: set) -> List[RecommendedJob]:
        jobs = []
        last_job_count = 0
        no_new_jobs_count = 0
        max_no_new_jobs = 5
        
        await self._load_all_jobs_on_page()
        
        while len(jobs) < limit and no_new_jobs_count < max_no_new_jobs:
            new_jobs = await self._extract_jobs_from_page(limit, seen_job_ids)
            
            for job in new_jobs:
                if job.job_id not in seen_job_ids and len(jobs) < limit:
                    jobs.append(job)
                    seen_job_ids.add(job.job_id)
            
            if len(jobs) == last_job_count:
                no_new_jobs_count += 1
                await self._fallback_scroll()
                await self.wait_and_focus(0.5)
            else:
                no_new_jobs_count = 0
            
            last_job_count = len(jobs)
            
            if len(jobs) >= limit:
                break
        
        return jobs

    async def _load_all_jobs_on_page(self) -> None:
        try:
            await self.page.evaluate("""
                (async () => {
                    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
                    const items = document.querySelectorAll('.scaffold-layout__list-item');
                    for (let i = 0; i < items.length; i++) {
                        items[i].scrollIntoView({ behavior: 'instant', block: 'center' });
                        await sleep(150);
                    }
                    const container = document.querySelector('.scaffold-layout__list');
                    if (container) dictionary_scrollTop = 0;
                })()
            """)
            await self.wait_and_focus(1)
            job_count = await self.page.locator('[data-job-id]').count()
            logger.info(f"Loaded {job_count} job cards on current page")
        except Exception as e:
            logger.warning(f"Error loading jobs on page: {e}")
            await self._fallback_scroll()
    
    async def _fallback_scroll(self) -> None:
        try:
            for _ in range(5):
                await self.page.keyboard.press('End')
                await self.wait_and_focus(0.5)
        except Exception as e:
            logger.debug(f"Fallback scroll error: {e}")

    async def _go_to_next_page(self) -> bool:
        try:
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
        try:
            job_card = self.page.locator(f'[data-job-id="{job_id}"]').first
            if await job_card.count() == 0:
                job_card = self.page.locator(f'a[href*="/jobs/view/{job_id}"]').first
            
            if await job_card.count() > 0:
                await job_card.click()
                await self.wait_and_focus(3.0)
                
                description = await self._extract_job_description()
                hiring_team = await self._extract_hiring_team()
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
                        description = await desc_elem.inner_text()
                        if description:
                            description = description.strip()
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
        try:
            hiring_team = []
            hiring_section_selectors = [
                '.job-details-people-who-can-help__section',
                '.hirer-card__hirer-information',
                '[class*="hiring-team"]',
            ]
            for section_selector in hiring_section_selectors:
                sections = await self.page.locator(section_selector).all()
                if sections:
                    break
            
            hirer_cards = await self.page.locator('.hirer-card__hirer-information, .job-details-people-who-can-help__section .display-flex.align-items-center').all()
            
            for card in hirer_cards:
                try:
                    member = {}
                    name_elem = card.locator('.jobs-poster__name strong, [class*="name"] strong').first
                    if await name_elem.count() > 0:
                        member['name'] = (await name_elem.inner_text()).strip()
                    else:
                        name_link = card.locator('a[href*="/in/"]').first
                        if await name_link.count() > 0:
                            name_text = await name_link.inner_text()
                            if name_text:
                                member['name'] = name_text.strip().split('\\n')[0]
                    
                    if not member.get('name'):
                        continue
                    
                    profile_link = card.locator('a[href*="/in/"]').first
                    if await profile_link.count() > 0:
                        href = await profile_link.get_attribute('href')
                        if href:
                            if not href.startswith('http'):
                                href = f"https://www.linkedin.com{href}"
                            member['profile_url'] = href.split('?')[0]
                    
                    title_selectors = ['.linked-area .text-body-small', '.hirer-card__job-poster', '[class*="subtitle"]']
                    for title_selector in title_selectors:
                        title_elem = card.locator(title_selector).first
                        if await title_elem.count() > 0:
                            title_text = await title_elem.inner_text()
                            if title_text and 'Job poster' not in title_text:
                                member['title'] = title_text.strip()
                                break
                    
                    degree_elem = card.locator('.hirer-card__connection-degree, [class*="connection-degree"]').first
                    if await degree_elem.count() > 0:
                        member['connection_degree'] = (await degree_elem.inner_text()).strip()
                    
                    card_text = await card.inner_text()
                    member['is_job_poster'] = 'job poster' in card_text.lower()
                    
                    if 'mutual connection' in card_text.lower():
                        import re
                        match = re.search(r'(\d+)\s*mutual\s*connection', card_text.lower())
                        if match:
                            member['mutual_connections'] = match.group(1)
                    
                    hiring_team.append(member)
                except Exception:
                    continue
            return hiring_team if hiring_team else None
        except Exception as e:
            logger.debug(f"Error extracting hiring team: {e}")
            return None

    async def _extract_match_analysis(self) -> Optional[Dict[str, Any]]:
        try:
            match_btn_selectors = [
                'button[aria-label="Show match details"]',
                'button:has-text("Show match details")',
                'a:has-text("Show match details")',
                'a[aria-label="Show match details"]',
                '.coach-shared-hscroll-button__action--guide-prompt',
            ]
            show_button = None
            for _ in range(6):
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
                return None
            
            await show_button.click()
            await self.wait_and_focus(4.0)
            
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
                        break
                except:
                    continue
            
            if not analysis_elem:
                return None
            
            analysis_text = await analysis_elem.inner_text()
            if not analysis_text:
                return None
            
            import re
            result = {
                'raw_text': analysis_text.strip(),
                'summary': None,
                'matched_qualifications': [],
                'missing_qualifications': [],
                'total_required': None,
                'total_matched': None,
            }
            
            lines = analysis_text.split('\\n')
            for line in lines:
                line = line.strip()
                if 'top applicant' in line.lower() or 'strong match' in line.lower() or 'good match' in line.lower():
                    result['summary'] = line
                    break
                elif line and not line.startswith('✓') and not line.startswith('?') and 'qualification' not in line.lower():
                    if not result['summary']:
                        result['summary'] = line
            
            match_count = re.search(r'matches?\s+(\d+)\s+of\s+(?:the\s+)?(\d+)\s+required', analysis_text.lower())
            if match_count:
                result['total_matched'] = int(match_count.group(1))
                result['total_required'] = int(match_count.group(2))
            
            for line in lines:
                line = line.strip()
                if line.startswith('✓'):
                    qual = line[1:].strip()
                    if qual:
                        result['matched_qualifications'].append(qual)
            
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

    async def _extract_jobs_from_page(self, limit: int, seen_job_ids: set) -> List[RecommendedJob]:
        jobs = []
        try:
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
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error extracting jobs: {e}")
        return jobs

    async def _wait_for_jobs_list(self, timeout: int = 15000) -> None:
        try:
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
                    return
                except:
                    continue
            await self.wait_and_focus(2)
        except Exception:
            await self.wait_and_focus(3)

    async def _parse_job_card(self, card) -> Optional[RecommendedJob]:
        try:
            job_id = await card.get_attribute("data-job-id")
            if not job_id:
                link = card.locator('a.job-card-container__link, a[data-control-name="job_card_title"]').first
                if await link.count() > 0:
                    href = await link.get_attribute("href")
                    import re
                    match = re.search(r'/view/(\d+)', href)
                    if match:
                        job_id = match.group(1)
            
            if not job_id:
                return None
            
            title_elem = card.locator('.job-card-list__title, strong, .artdeco-entity-lockup__title').first
            title = (await title_elem.inner_text()).strip() if await title_elem.count() > 0 else "Unknown Title"
            
            company_elem = card.locator('.job-card-container__primary-description, .artdeco-entity-lockup__subtitle').first
            company = (await company_elem.inner_text()).strip() if await company_elem.count() > 0 else "Unknown Company"
            
            location_elem = card.locator('.job-card-container__metadata-item, .artdeco-entity-lockup__caption').first
            location = (await location_elem.inner_text()).strip() if await location_elem.count() > 0 else None
            
            footer_item = card.locator('.job-card-list__footer-wrapper li').first
            footer_text = (await footer_item.inner_text()).strip() if await footer_item.count() > 0 else None
            actively_hiring = footer_text and "Actively recruiting" in footer_text
            promoted = footer_text and "Promoted" in footer_text
            
            easy_apply_elem = card.locator('.job-card-container__apply-method').first
            easy_apply = (await easy_apply_elem.count() > 0)
            
            job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            
            return RecommendedJob(
                job_id=job_id,
                job_url=job_url,
                collection=self.collection.value,
                title=title,
                company=company,
                location=location,
                actively_hiring=actively_hiring,
                promoted=promoted,
                easy_apply=easy_apply
            )
            
        except Exception as e:
            logger.debug(f"Error parsing job card: {e}")
            return None
