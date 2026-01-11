-- Run this in the Supabase SQL Editor

-- 1. Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Enable RLS
ALTER TABLE "Public_School_Location" ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow public read access" ON "Public_School_Location";

CREATE POLICY "Allow public read access"
ON "Public_School_Location"
FOR SELECT
TO anon
USING (true);

-- 3. Create the Spatial Search Function
-- Drops old version first
DROP FUNCTION IF EXISTS get_nearby_schools(float, float, float);

CREATE OR REPLACE FUNCTION get_nearby_schools(user_lat float, user_lon float, radius_miles float)
RETURNS TABLE (
  name text,
  address text,
  city text,
  state text,
  zip text,
  nces_id text,
  dist_miles float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    s."NAME"::text AS name,
    s."STREET"::text AS address,  -- Column is STREET in your table
    s."CITY"::text AS city,
    s."STATE"::text AS state,
    s."ZIP"::text AS zip,
    s."NCES_id"::text AS nces_id, -- Column is NCES_id
    (ST_Distance(
      ST_SetSRID(ST_MakePoint(s."LON", s."LAT"), 4326)::geography,
      ST_SetSRID(ST_MakePoint(user_lon, user_lat), 4326)::geography
    ) / 1609.34) AS dist_miles
  FROM
    "Public_School_Location" s
  WHERE
    ST_DWithin(
      ST_SetSRID(ST_MakePoint(s."LON", s."LAT"), 4326)::geography,
      ST_SetSRID(ST_MakePoint(user_lon, user_lat), 4326)::geography,
      radius_miles * 1609.34
    )
  ORDER BY
    dist_miles ASC
  LIMIT 50;
END;
$$;
