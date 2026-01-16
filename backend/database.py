import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client
from linkedin_scraper.models.job import RecommendedJob

load_dotenv()


class Database:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")
        self.client: Client = None
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                print("✓ Supabase client initialized")
            except Exception as e:
                print(f"✗ Failed to initialize Supabase client: {e}")
        else:
            print("⚠ SUPABASE_URL and SUPABASE_KEY must be set directly or via .env")

    def upsert_jobs(self, jobs: List[RecommendedJob], owner_id: str = None) -> bool:
        """
        Upsert a list of jobs into the 'career_board' table.
        """
        if not self.client:
            print("⚠ Supabase client not initialized, skipping DB save")
            return False
            
        try:
            # Convert Pydantic models to dicts
            data_to_insert = []
            for job in jobs:
                # model_dump() for Pydantic v2
                job_dict = job.model_dump()
                if owner_id:
                    job_dict['owner_id'] = owner_id
                # Ensure complex types are JSON-compatible (API usually handles this, 
                # but Supabase python client might want explicit types)
                data_to_insert.append(job_dict)
            
            # Upsert into career_board
            # Assuming job_id is the primary key or unique constraint
            response = self.client.table("career_board").upsert(
                data_to_insert, 
                on_conflict="job_id"
            ).execute()
            
            print(f"✓ Upserted {len(data_to_insert)} jobs to Supabase")
            return True
            
        except Exception as e:
            print(f"✗ Error upserting jobs to Supabase: {e}")
            return False

# Singleton instance
db = Database()
