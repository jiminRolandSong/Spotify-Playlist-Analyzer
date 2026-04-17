-- stg_tracks: raw 데이터 정제 레이어
-- playlist_tracks에서 필요한 컬럼만 골라서 타입/이름 정리

SELECT
    track_id,
    track_name,
    track_duration_sec,
    track_popularity,
    album_id,
    album_name,
    album_release_date::DATE AS release_date,
    release_year,
    artist_names,
    track_genres,
    playlist_id
FROM {{ source('spotify_raw', 'playlist_tracks') }}
WHERE track_id IS NOT NULL