-- Supabase Migration for 'career_board' table
-- Matches the RecommendedJob data model
-- Includes owner_id for user ownership

DROP TABLE IF EXISTS career_board CASCADE;

CREATE TABLE career_board (
    job_id TEXT PRIMARY KEY,
    job_url TEXT,
    collection TEXT,
    title TEXT,
    company TEXT,
    company_url TEXT,
    location TEXT,
    posted_time TEXT,
    employment_type TEXT,
    workplace_type TEXT,
    promoted BOOLEAN DEFAULT FALSE,
    easy_apply BOOLEAN DEFAULT FALSE,
    actively_hiring BOOLEAN DEFAULT FALSE,
    description TEXT,
    hiring_team JSONB,
    match_analysis JSONB,
    owner_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for filtering by collection
CREATE INDEX IF NOT EXISTS idx_career_board_collection ON career_board(collection);
-- Index for filtering by owner
CREATE INDEX IF NOT EXISTS idx_career_board_owner_id ON career_board(owner_id);

-- Function to automatically update 'updated_at' on changes
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_career_board_updated_at ON career_board;
CREATE TRIGGER update_career_board_updated_at
    BEFORE UPDATE ON career_board
    FOR EACH ROW
    EXECUTE PROCEDURE update_updated_at_column();
