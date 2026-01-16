import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import db
from backend.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Check DB connection
    if not db.client:
        print("⚠ Supabase client not initialized. Please set SUPABASE_URL and SUPABASE_KEY.")
    yield
    # Shutdown: Clean up resources if needed
    print("Shutting down...")

app = FastAPI(title="LinkedIn Jobs API", lifespan=lifespan)
app.include_router(router)

# Configure CORS for Next.js
origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "LinkedIn Jobs API is running"}

@app.get("/health")
async def health_check():
    status = "healthy" if db.client else "degraded (no db)"
    return {"status": status}
