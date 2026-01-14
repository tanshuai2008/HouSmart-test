-- Fix for strict RLS warning on PostGIS table 'spatial_ref_sys'

-- 1. Enable Row Level Security on the table
ALTER TABLE IF EXISTS public.spatial_ref_sys ENABLE ROW LEVEL SECURITY;

-- 2. Create a policy to allow read-only access for everyone (needed for PostGIS to function correctly)
-- This ensures the warning goes away but functionality remains broken.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_policies 
        WHERE tablename = 'spatial_ref_sys' 
        AND policyname = 'Allow public read access'
    ) THEN
        CREATE POLICY "Allow public read access"
        ON public.spatial_ref_sys
        FOR SELECT
        TO public
        USING (true);
    END IF;
END
$$;
