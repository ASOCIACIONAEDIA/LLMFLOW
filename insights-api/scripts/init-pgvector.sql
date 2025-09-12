-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify the extension was created successfully
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE NOTICE 'pgvector extension is available and ready!';
    ELSE
        RAISE EXCEPTION 'pgvector extension failed to install!';
    END IF;
END $$;