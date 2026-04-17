-- mart_track_stats: 앨범별 트랙 통계 집계
SELECT
    album_name,
    release_year,
    COUNT(*)                        AS track_count,
    ROUND(AVG(track_popularity), 1) AS avg_popularity,
    ROUND(AVG(track_duration_sec)::NUMERIC, 1) AS avg_duration_sec,
    MAX(track_popularity)           AS max_popularity,
    MIN(track_popularity)           AS min_popularity
FROM {{ ref('stg_tracks') }}
GROUP BY album_name, release_year
ORDER BY avg_popularity DESC