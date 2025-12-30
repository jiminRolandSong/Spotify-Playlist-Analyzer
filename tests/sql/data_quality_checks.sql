-- =====================================================
-- SQL Data Quality & Integrity Checks
-- Validates database constraints, duplicates, and UPSERT logic
-- =====================================================

-- =====================================================
-- 1. DUPLICATE DETECTION TESTS
-- =====================================================

-- Check for duplicate tracks within same playlist (should return 0)
-- Tests that composite primary key (playlist_id, track_id) prevents duplicates
SELECT
    playlist_id,
    track_id,
    COUNT(*) as duplicate_count
FROM playlist_tracks
GROUP BY playlist_id, track_id
HAVING COUNT(*) > 1;

-- Expected Result: 0 rows (no duplicates)
-- If rows returned: PRIMARY KEY constraint violated


-- =====================================================
-- 2. NULL VALUE CHECKS
-- =====================================================

-- Check for NULL values in required fields
SELECT
    'playlist_id' as field_name,
    COUNT(*) as null_count
FROM playlist_tracks
WHERE playlist_id IS NULL

UNION ALL

SELECT
    'track_id' as field_name,
    COUNT(*) as null_count
FROM playlist_tracks
WHERE track_id IS NULL

UNION ALL

SELECT
    'track_name' as field_name,
    COUNT(*) as null_count
FROM playlist_tracks
WHERE track_name IS NULL

UNION ALL

SELECT
    'track_duration_ms' as field_name,
    COUNT(*) as null_count
FROM playlist_tracks
WHERE track_duration_ms IS NULL;

-- Expected Result: All null_count = 0
-- If null_count > 0: Data quality issue, missing required fields


-- =====================================================
-- 3. DATA TYPE & RANGE VALIDATION
-- =====================================================

-- Check track_popularity is within valid range (0-100)
SELECT
    track_id,
    track_name,
    track_popularity
FROM playlist_tracks
WHERE track_popularity < 0 OR track_popularity > 100;

-- Expected Result: 0 rows
-- If rows returned: Invalid data - popularity out of range


-- Check track_duration_ms is positive
SELECT
    track_id,
    track_name,
    track_duration_ms
FROM playlist_tracks
WHERE track_duration_ms <= 0;

-- Expected Result: 0 rows
-- If rows returned: Invalid data - negative or zero duration


-- Check release_date format (should be valid DATE)
SELECT
    track_id,
    album_name,
    album_release_date
FROM playlist_tracks
WHERE album_release_date IS NOT NULL
  AND album_release_date NOT BETWEEN '1900-01-01' AND '2100-12-31';

-- Expected Result: 0 rows
-- If rows returned: Invalid date values


-- =====================================================
-- 4. JSONB FIELD VALIDATION
-- =====================================================

-- Check that track_genres is valid JSONB array
SELECT
    track_id,
    track_name,
    track_genres
FROM playlist_tracks
WHERE jsonb_typeof(track_genres) != 'array';

-- Expected Result: 0 rows
-- If rows returned: Invalid JSONB structure


-- Check that artist_names is valid JSONB array
SELECT
    track_id,
    track_name,
    artist_names
FROM playlist_tracks
WHERE jsonb_typeof(artist_names) != 'array';

-- Expected Result: 0 rows


-- Check that artist_names array is not empty
SELECT
    track_id,
    track_name,
    artist_names
FROM playlist_tracks
WHERE jsonb_array_length(artist_names) = 0;

-- Expected Result: 0 rows
-- If rows returned: Business rule violation - every track must have at least one artist


-- =====================================================
-- 5. REFERENTIAL INTEGRITY CHECKS
-- =====================================================

-- Check for orphaned tracks (tracks without valid playlist reference)
-- Note: This assumes playlist metadata is stored in a separate table
-- Modify if your schema differs
-- SELECT
--     pt.playlist_id,
--     COUNT(*) as track_count
-- FROM playlist_tracks pt
-- LEFT JOIN playlists p ON pt.playlist_id = p.playlist_id
-- WHERE p.playlist_id IS NULL
-- GROUP BY pt.playlist_id;

-- Expected Result: 0 rows
-- If rows returned: Orphaned records - tracks exist for non-existent playlists


-- =====================================================
-- 6. DATA COMPLETENESS CHECKS
-- =====================================================

-- Check for tracks with missing album information
SELECT
    COUNT(*) as tracks_missing_album
FROM playlist_tracks
WHERE album_id IS NULL OR album_name IS NULL;

-- Expected Result: 0 (or low percentage if partial data is acceptable)


-- Check percentage of tracks with populated genres
SELECT
    COUNT(CASE WHEN jsonb_array_length(track_genres) > 0 THEN 1 END) * 100.0 / COUNT(*) as genre_coverage_pct
FROM playlist_tracks;

-- Expected Result: Close to 100%
-- If low: Data enrichment issue - genre fetching may be failing


-- =====================================================
-- 7. UPSERT IDEMPOTENCY TEST
-- =====================================================

-- Verify that re-running UPSERT updates records instead of creating duplicates
-- This query should be run BEFORE and AFTER re-running the load process
-- The count should remain the same if UPSERT is working correctly

SELECT
    playlist_id,
    COUNT(*) as total_tracks,
    COUNT(DISTINCT track_id) as unique_tracks,
    COUNT(*) - COUNT(DISTINCT track_id) as duplicate_count
FROM playlist_tracks
GROUP BY playlist_id
HAVING COUNT(*) != COUNT(DISTINCT track_id);

-- Expected Result: 0 rows (total_tracks = unique_tracks)
-- If rows returned: UPSERT logic failing - duplicates being created


-- =====================================================
-- 8. DATA CONSISTENCY CHECKS
-- =====================================================

-- Check for inconsistent track data (same track_id with different metadata across playlists)
WITH track_variants AS (
    SELECT
        track_id,
        COUNT(DISTINCT track_name) as name_variants,
        COUNT(DISTINCT album_id) as album_variants,
        COUNT(DISTINCT track_duration_ms) as duration_variants
    FROM playlist_tracks
    GROUP BY track_id
)
SELECT
    track_id,
    name_variants,
    album_variants,
    duration_variants
FROM track_variants
WHERE name_variants > 1 OR duration_variants > 1;

-- Expected Result: 0 rows (same track should have same metadata)
-- If rows returned: Data inconsistency - investigate track metadata updates


-- =====================================================
-- 9. STATISTICAL OUTLIER DETECTION
-- =====================================================

-- Find tracks with unusually long duration (> 15 minutes = 900,000 ms)
SELECT
    track_id,
    track_name,
    track_duration_ms,
    track_duration_ms / 60000.0 as duration_minutes
FROM playlist_tracks
WHERE track_duration_ms > 900000;

-- Expected Result: Few rows (podcasts, live recordings)
-- Manual review recommended for tracks > 15 minutes


-- Find tracks with zero popularity (may indicate data quality issue)
SELECT
    track_id,
    track_name,
    track_popularity
FROM playlist_tracks
WHERE track_popularity = 0;

-- Expected Result: Some rows acceptable (new/obscure tracks)
-- High percentage suggests data fetching issue


-- =====================================================
-- 10. DATA FRESHNESS CHECK
-- =====================================================

-- Check for tracks with future release dates (data quality issue)
SELECT
    track_id,
    album_name,
    album_release_date
FROM playlist_tracks
WHERE album_release_date > CURRENT_DATE;

-- Expected Result: 0 rows (or very few for pre-releases)
-- If many rows: Invalid date data or system clock issue


-- =====================================================
-- SUMMARY REPORT
-- =====================================================

-- Generate comprehensive data quality summary
SELECT
    COUNT(*) as total_tracks,
    COUNT(DISTINCT track_id) as unique_tracks,
    COUNT(DISTINCT playlist_id) as total_playlists,
    COUNT(CASE WHEN track_popularity > 0 THEN 1 END) * 100.0 / COUNT(*) as pct_with_popularity,
    COUNT(CASE WHEN jsonb_array_length(track_genres) > 0 THEN 1 END) * 100.0 / COUNT(*) as pct_with_genres,
    COUNT(CASE WHEN album_release_date IS NOT NULL THEN 1 END) * 100.0 / COUNT(*) as pct_with_release_date,
    AVG(track_duration_ms) / 1000.0 as avg_duration_seconds,
    MIN(track_duration_ms) / 1000.0 as min_duration_seconds,
    MAX(track_duration_ms) / 1000.0 as max_duration_seconds
FROM playlist_tracks;

-- Expected Result:
-- - total_tracks = unique_tracks (no duplicates)
-- - All percentages > 95% (good data coverage)
-- - Avg duration 180-240 seconds (typical song length)
