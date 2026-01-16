# Frontend Developer Guide (Next.js)

## 🔗 Backend API
*   **Base URL**: `http://localhost:8000` (Local)
*   **Status**: Running

## 🛠️ Integration Pattern

### 1. Triggering a Scrape
Do not scrape directly from the browser. Call the Python Backend.

**Endpoint**: `POST /api/scrape`

**Request**:
```typescript
const startScrape = async (collection: string) => {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) throw new Error("Must be logged in");

  const response = await fetch('http://localhost:8000/api/scrape', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      collection: collection, // e.g. "top-applicant"
      limit: 10,
      details: true,
      owner_id: user.id // <--- CRITICAL: Pass the Supabase User ID
    })
  });
  
  const data = await response.json();
  return data.job_id; // Store this to track status
}
```

### 2. Tracking Progress
Poll the status endpoint to show a progress bar.

**Endpoint**: `GET /api/jobs/{job_id}`

```typescript
// Response
{
  "id": "...",
  "status": "running", // running | completed | failed
  "progress": 45,      // 0-100
  "message": "Processing page 1...",
  "jobs_collected": 5
}
```

### 3. Displaying Jobs
Fetch data **directly from Supabase** for the best performance and real-time updates. The Python backend inserts rows into the `career_board` table.

```typescript
const { data: jobs } = await supabase
  .from('career_board')
  .select('*')
  .eq('owner_id', user.id) // Filter by current user
  .order('created_at', { ascending: false });
```

## 📊 Data Types

### Job object (Supabase `career_board`)
```typescript
interface Job {
  job_id: string;
  title: string;
  company: string;
  location: string;
  match_analysis: {
    summary: string;
    total_matched: number;
    total_required: number;
    matched_qualifications: string[];
    missing_qualifications: string[];
  };
  hiring_team: {
    name: string;
    title: string;
    profile_url: string;
  }[];
  // ... other fields
}
```

### Collection Options
Fetch from `GET /api/collections` to populate your dropdown.
