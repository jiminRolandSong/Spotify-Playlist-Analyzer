"""
Unit tests for the transformation layer (scripts/transform.py)
Tests data cleaning, type conversions, and feature engineering
"""
import unittest
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.transform import transform_playlist_df


class TestTransformPlaylistDF(unittest.TestCase):
    """Test data transformation logic"""

    def setUp(self):
        """Create sample raw data for testing"""
        self.sample_raw_data = pd.DataFrame({
            'track_id': ['track1', 'track2', 'track3'],
            'track_name': ['Song 1', 'Song 2', 'Song 3'],
            'track_duration_ms': [200000, 180000, 240000],
            'track_popularity': [80, None, 90],  # Test null handling
            'album_name': ['Album 1', None, 'Album 3'],  # Test null handling
            'album_release_date': ['2023-01-15', '2022-06-20', 'invalid_date'],  # Test date parsing
            'artist_names': ['["Artist 1", "Artist 2"]', ['Artist 3'], '["Artist 4"]'],  # Mixed types
            'track_genres': ['["pop", "rock"]', ['jazz'], []],  # Mixed types
            'artist_ids': ['["id1", "id2"]', ['id3'], '["id4"]'],  # Mixed types
        })

    def test_transform_creates_duration_in_seconds(self):
        """Test that duration is converted from milliseconds to seconds"""
        result = transform_playlist_df(self.sample_raw_data.copy())

        self.assertIn('track_duration_sec', result.columns)
        self.assertEqual(result.iloc[0]['track_duration_sec'], 200.0)
        self.assertEqual(result.iloc[1]['track_duration_sec'], 180.0)

    def test_transform_creates_release_year(self):
        """Test that release year is extracted from date"""
        result = transform_playlist_df(self.sample_raw_data.copy())

        self.assertIn('release_year', result.columns)
        self.assertEqual(result.iloc[0]['release_year'], 2023)
        self.assertEqual(result.iloc[1]['release_year'], 2022)

    def test_transform_handles_null_popularity(self):
        """Test that null popularity values are filled with 0"""
        result = transform_playlist_df(self.sample_raw_data.copy())

        self.assertEqual(result.iloc[1]['track_popularity'], 0)  # Was None
        self.assertEqual(result.iloc[0]['track_popularity'], 80)  # Was 80

    def test_transform_handles_null_album_name(self):
        """Test that null album names are replaced with 'Unknown'"""
        result = transform_playlist_df(self.sample_raw_data.copy())

        self.assertEqual(result.iloc[1]['album_name'], 'Unknown')
        self.assertEqual(result.iloc[0]['album_name'], 'Album 1')

    def test_transform_parses_string_lists(self):
        """Test that string representations of lists are parsed correctly"""
        result = transform_playlist_df(self.sample_raw_data.copy())

        # Check artist_names
        self.assertIsInstance(result.iloc[0]['artist_names'], list)
        self.assertEqual(result.iloc[0]['artist_names'], ['Artist 1', 'Artist 2'])

        # Check track_genres
        self.assertIsInstance(result.iloc[0]['track_genres'], list)
        self.assertEqual(result.iloc[0]['track_genres'], ['pop', 'rock'])

    def test_transform_preserves_existing_lists(self):
        """Test that columns already containing lists are preserved"""
        result = transform_playlist_df(self.sample_raw_data.copy())

        # Row 1 already had a list (not a string)
        self.assertIsInstance(result.iloc[1]['artist_names'], list)
        self.assertEqual(result.iloc[1]['artist_names'], ['Artist 3'])

    def test_transform_handles_empty_lists(self):
        """Test that empty lists are handled correctly"""
        result = transform_playlist_df(self.sample_raw_data.copy())

        # Row 2 has empty genre list
        self.assertIsInstance(result.iloc[2]['track_genres'], list)
        self.assertEqual(result.iloc[2]['track_genres'], [])

    def test_transform_handles_invalid_dates(self):
        """Test that invalid dates result in NaT/None for year"""
        result = transform_playlist_df(self.sample_raw_data.copy())

        # Row 2 has invalid date
        self.assertTrue(pd.isna(result.iloc[2]['release_year']))

    def test_transform_preserves_required_columns(self):
        """Test that all required columns are present in output"""
        result = transform_playlist_df(self.sample_raw_data.copy())

        required_cols = [
            'track_id', 'track_name', 'track_duration_ms', 'track_duration_sec',
            'track_popularity', 'album_name', 'album_release_date', 'release_year',
            'artist_names', 'track_genres', 'artist_ids'
        ]

        for col in required_cols:
            self.assertIn(col, result.columns, f"Missing required column: {col}")

    def test_transform_data_types(self):
        """Test that data types are correct after transformation"""
        result = transform_playlist_df(self.sample_raw_data.copy())

        # Check integer types
        self.assertEqual(result['track_popularity'].dtype, 'int64')

        # Check float types
        self.assertEqual(result['track_duration_sec'].dtype, 'float64')

        # Check that lists are objects
        self.assertEqual(result['artist_names'].dtype, 'object')


class TestTransformEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_transform_empty_dataframe(self):
        """Test transformation of empty DataFrame"""
        empty_df = pd.DataFrame(columns=[
            'track_id', 'track_name', 'track_duration_ms', 'track_popularity',
            'album_name', 'album_release_date', 'artist_names', 'track_genres', 'artist_ids'
        ])

        result = transform_playlist_df(empty_df)

        self.assertEqual(len(result), 0)
        self.assertIn('track_duration_sec', result.columns)

    def test_transform_all_null_values(self):
        """Test transformation with all null values"""
        null_df = pd.DataFrame({
            'track_id': ['track1'],
            'track_name': [None],
            'track_duration_ms': [None],
            'track_popularity': [None],
            'album_name': [None],
            'album_release_date': [None],
            'artist_names': [None],
            'track_genres': [None],
            'artist_ids': [None],
        })

        result = transform_playlist_df(null_df)

        # Should handle without errors
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['track_popularity'], 0)
        self.assertEqual(result.iloc[0]['album_name'], 'Unknown')


if __name__ == '__main__':
    unittest.main()
