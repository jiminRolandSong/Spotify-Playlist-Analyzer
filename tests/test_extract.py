"""
Unit tests for the extraction layer (scripts/extract.py)
Tests Spotify API integration, pagination, and data extraction logic
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import sys
import os

# Add parent directory to path to import scripts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.extract import spotify_api_setup, extract_playlist_tracks


class TestSpotifyAPISetup(unittest.TestCase):
    """Test Spotify API authentication and setup"""

    @patch('scripts.extract.load_dotenv')
    @patch('scripts.extract.os.getenv')
    @patch('scripts.extract.SpotifyClientCredentials')
    @patch('scripts.extract.spotipy.Spotify')
    def test_spotify_api_setup_local_env(self, mock_spotify, mock_credentials, mock_getenv, mock_load_dotenv):
        """Test API setup with local environment configuration"""
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            'ENV_MODE': 'local',
            'SPOTIPY_CLIENT_ID': 'test_client_id',
            'SPOTIPY_CLIENT_SECRET': 'test_client_secret'
        }.get(key, default)

        # Call the function
        result = spotify_api_setup()

        # Assertions
        mock_load_dotenv.assert_called_once()
        mock_credentials.assert_called_once_with(
            client_id='test_client_id',
            client_secret='test_client_secret'
        )
        mock_spotify.assert_called_once()
        self.assertIsNotNone(result)

    @patch('scripts.extract.load_dotenv')
    @patch('scripts.extract.os.getenv')
    @patch('scripts.extract.SpotifyClientCredentials')
    @patch('scripts.extract.spotipy.Spotify')
    def test_spotify_api_setup_docker_env(self, mock_spotify, mock_credentials, mock_getenv, mock_load_dotenv):
        """Test API setup with Docker environment configuration"""
        # Mock environment variables for Docker mode
        mock_getenv.side_effect = lambda key, default=None: {
            'ENV_MODE': 'docker',
            'SPOTIPY_CLIENT_ID': 'docker_client_id',
            'SPOTIPY_CLIENT_SECRET': 'docker_client_secret'
        }.get(key, default)

        # Call the function
        result = spotify_api_setup()

        # Verify .env.docker was loaded
        self.assertIsNotNone(result)


class TestExtractPlaylistTracks(unittest.TestCase):
    """Test playlist track extraction with mocked Spotify API"""

    def setUp(self):
        """Set up mock Spotify client for tests"""
        self.mock_sp = Mock()
        self.test_playlist_id = 'test_playlist_123'

    def test_extract_playlist_tracks_single_page(self):
        """Test extraction of playlist with single page of tracks"""
        # Mock playlist info
        self.mock_sp.playlist.return_value = {
            'name': 'Test Playlist',
            'owner': {'display_name': 'Test Owner'}
        }

        # Mock single page of tracks
        self.mock_sp.playlist_items.return_value = {
            'items': [
                {
                    'track': {
                        'id': 'track1',
                        'name': 'Test Track 1',
                        'duration_ms': 200000,
                        'popularity': 80,
                        'album': {
                            'id': 'album1',
                            'name': 'Test Album',
                            'release_date': '2023-01-01',
                            'label': 'Test Label'
                        },
                        'artists': [
                            {'id': 'artist1', 'name': 'Test Artist'}
                        ]
                    }
                }
            ],
            'next': None  # No more pages
        }

        # Mock artist info for genre fetching
        self.mock_sp.artist.return_value = {
            'genres': ['pop', 'rock']
        }

        # Call the function
        df, metadata = extract_playlist_tracks(self.mock_sp, self.test_playlist_id)

        # Assertions
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)
        self.assertEqual(metadata['name'], 'Test Playlist')
        self.assertEqual(metadata['owner'], 'Test Owner')
        self.assertEqual(df.iloc[0]['track_name'], 'Test Track 1')
        self.assertIn('pop', df.iloc[0]['track_genres'])

    def test_extract_playlist_tracks_pagination(self):
        """Test extraction with multiple pages (pagination)"""
        # Mock playlist info
        self.mock_sp.playlist.return_value = {
            'name': 'Large Playlist',
            'owner': {'display_name': 'Test Owner'}
        }

        # Mock first page
        page1 = {
            'items': [
                {
                    'track': {
                        'id': f'track{i}',
                        'name': f'Track {i}',
                        'duration_ms': 200000,
                        'popularity': 80,
                        'album': {
                            'id': 'album1',
                            'name': 'Album',
                            'release_date': '2023-01-01',
                            'label': 'Label'
                        },
                        'artists': [{'id': 'artist1', 'name': 'Artist'}]
                    }
                } for i in range(3)
            ],
            'next': 'next_page_url'
        }

        # Mock second page
        page2 = {
            'items': [
                {
                    'track': {
                        'id': 'track3',
                        'name': 'Track 3',
                        'duration_ms': 200000,
                        'popularity': 80,
                        'album': {
                            'id': 'album1',
                            'name': 'Album',
                            'release_date': '2023-01-01',
                            'label': 'Label'
                        },
                        'artists': [{'id': 'artist1', 'name': 'Artist'}]
                    }
                }
            ],
            'next': None
        }

        self.mock_sp.playlist_items.return_value = page1
        self.mock_sp.next.return_value = page2
        self.mock_sp.artist.return_value = {'genres': ['pop']}

        # Call the function
        df, metadata = extract_playlist_tracks(self.mock_sp, self.test_playlist_id)

        # Assertions
        self.assertEqual(len(df), 4)  # 3 from page1 + 1 from page2
        self.mock_sp.next.assert_called_once()

    def test_extract_handles_missing_track(self):
        """Test that None/missing tracks are skipped"""
        self.mock_sp.playlist.return_value = {
            'name': 'Test Playlist',
            'owner': {'display_name': 'Test Owner'}
        }

        # Mock response with a None track (deleted/unavailable)
        self.mock_sp.playlist_items.return_value = {
            'items': [
                {'track': None},  # Missing track
                {
                    'track': {
                        'id': 'track1',
                        'name': 'Valid Track',
                        'duration_ms': 200000,
                        'popularity': 80,
                        'album': {
                            'id': 'album1',
                            'name': 'Album',
                            'release_date': '2023-01-01',
                            'label': 'Label'
                        },
                        'artists': [{'id': 'artist1', 'name': 'Artist'}]
                    }
                }
            ],
            'next': None
        }

        self.mock_sp.artist.return_value = {'genres': []}

        # Call the function
        df, metadata = extract_playlist_tracks(self.mock_sp, self.test_playlist_id)

        # Should only have 1 track (None track skipped)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['track_name'], 'Valid Track')


if __name__ == '__main__':
    unittest.main()
