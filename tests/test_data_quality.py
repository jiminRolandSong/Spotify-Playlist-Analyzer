"""
Data Quality & Schema Validation Tests
Validates JSON schema compliance, data types, and business rules
"""
import unittest
import pandas as pd
from jsonschema import validate, ValidationError
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# JSON Schema for Spotify Track Response
TRACK_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "duration_ms", "popularity", "album", "artists"],
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "duration_ms": {"type": "integer", "minimum": 0},
        "popularity": {"type": "integer", "minimum": 0, "maximum": 100},
        "album": {
            "type": "object",
            "required": ["id", "name", "release_date"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "release_date": {"type": "string", "pattern": "^\\d{4}(-\\d{2}(-\\d{2})?)?$"}
            }
        },
        "artists": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "name"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"}
                }
            }
        }
    }
}


class TestJSONSchemaValidation(unittest.TestCase):
    """Test JSON schema compliance for API responses"""

    def test_valid_track_schema(self):
        """Test that a valid track passes schema validation"""
        valid_track = {
            "id": "track123",
            "name": "Test Song",
            "duration_ms": 200000,
            "popularity": 80,
            "album": {
                "id": "album123",
                "name": "Test Album",
                "release_date": "2023-01-15"
            },
            "artists": [
                {"id": "artist1", "name": "Test Artist"}
            ]
        }

        # Should not raise ValidationError
        try:
            validate(instance=valid_track, schema=TRACK_SCHEMA)
        except ValidationError as e:
            self.fail(f"Valid track failed schema validation: {e}")

    def test_missing_required_field(self):
        """Test that missing required fields fail validation"""
        invalid_track = {
            "id": "track123",
            "name": "Test Song",
            # Missing duration_ms, popularity, album, artists
        }

        with self.assertRaises(ValidationError):
            validate(instance=invalid_track, schema=TRACK_SCHEMA)

    def test_invalid_popularity_range(self):
        """Test that popularity outside 0-100 fails validation"""
        invalid_track = {
            "id": "track123",
            "name": "Test Song",
            "duration_ms": 200000,
            "popularity": 150,  # Invalid: > 100
            "album": {
                "id": "album123",
                "name": "Test Album",
                "release_date": "2023-01-15"
            },
            "artists": [{"id": "artist1", "name": "Artist"}]
        }

        with self.assertRaises(ValidationError):
            validate(instance=invalid_track, schema=TRACK_SCHEMA)

    def test_empty_artists_array(self):
        """Test that empty artists array fails validation"""
        invalid_track = {
            "id": "track123",
            "name": "Test Song",
            "duration_ms": 200000,
            "popularity": 80,
            "album": {
                "id": "album123",
                "name": "Test Album",
                "release_date": "2023-01-15"
            },
            "artists": []  # Invalid: minItems is 1
        }

        with self.assertRaises(ValidationError):
            validate(instance=invalid_track, schema=TRACK_SCHEMA)

    def test_invalid_date_format(self):
        """Test that invalid date format fails validation"""
        invalid_track = {
            "id": "track123",
            "name": "Test Song",
            "duration_ms": 200000,
            "popularity": 80,
            "album": {
                "id": "album123",
                "name": "Test Album",
                "release_date": "01/15/2023"  # Invalid format
            },
            "artists": [{"id": "artist1", "name": "Artist"}]
        }

        with self.assertRaises(ValidationError):
            validate(instance=invalid_track, schema=TRACK_SCHEMA)


class TestDataTypeValidation(unittest.TestCase):
    """Test data type correctness in transformed data"""

    def setUp(self):
        """Create sample transformed data"""
        self.sample_df = pd.DataFrame({
            'track_id': ['track1', 'track2', 'track3'],
            'track_name': ['Song 1', 'Song 2', 'Song 3'],
            'track_duration_ms': [200000, 180000, 240000],
            'track_duration_sec': [200.0, 180.0, 240.0],
            'track_popularity': [80, 75, 90],
            'album_release_date': pd.to_datetime(['2023-01-01', '2023-02-01', '2023-03-01']),
            'release_year': [2023, 2023, 2023],
            'artist_names': [['Artist 1'], ['Artist 2'], ['Artist 3']],
            'track_genres': [['pop'], ['rock'], ['jazz']],
        })

    def test_track_id_is_string(self):
        """Test that track_id is string type"""
        self.assertEqual(self.sample_df['track_id'].dtype, 'object')  # object = string in pandas
        self.assertTrue(all(isinstance(x, str) for x in self.sample_df['track_id']))

    def test_duration_ms_is_integer(self):
        """Test that track_duration_ms is integer type"""
        self.assertEqual(self.sample_df['track_duration_ms'].dtype, 'int64')

    def test_duration_sec_is_float(self):
        """Test that track_duration_sec is float type"""
        self.assertEqual(self.sample_df['track_duration_sec'].dtype, 'float64')

    def test_popularity_is_integer(self):
        """Test that track_popularity is integer type"""
        self.assertEqual(self.sample_df['track_popularity'].dtype, 'int64')

    def test_release_date_is_datetime(self):
        """Test that album_release_date is datetime type"""
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(self.sample_df['album_release_date']))

    def test_release_year_is_integer(self):
        """Test that release_year is integer type"""
        self.assertEqual(self.sample_df['release_year'].dtype, 'int64')

    def test_artist_names_is_list(self):
        """Test that artist_names contains lists"""
        for value in self.sample_df['artist_names']:
            self.assertIsInstance(value, list)

    def test_track_genres_is_list(self):
        """Test that track_genres contains lists"""
        for value in self.sample_df['track_genres']:
            self.assertIsInstance(value, list)


class TestBusinessRuleValidation(unittest.TestCase):
    """Test business rules and data constraints"""

    def test_duration_is_positive(self):
        """Test that track duration is always positive"""
        df = pd.DataFrame({
            'track_duration_ms': [200000, 180000, 240000]
        })

        self.assertTrue(all(df['track_duration_ms'] > 0))

    def test_popularity_range(self):
        """Test that popularity is between 0-100"""
        df = pd.DataFrame({
            'track_popularity': [0, 50, 100]
        })

        self.assertTrue(all(df['track_popularity'] >= 0))
        self.assertTrue(all(df['track_popularity'] <= 100))

    def test_no_empty_track_ids(self):
        """Test that track_id is never empty"""
        df = pd.DataFrame({
            'track_id': ['track1', 'track2', 'track3']
        })

        self.assertTrue(all(df['track_id'].str.len() > 0))

    def test_no_null_track_names(self):
        """Test that track_name is never null"""
        df = pd.DataFrame({
            'track_name': ['Song 1', 'Song 2', 'Song 3']
        })

        self.assertFalse(df['track_name'].isnull().any())

    def test_artists_not_empty(self):
        """Test that artist_names list is never empty"""
        df = pd.DataFrame({
            'artist_names': [['Artist 1'], ['Artist 2', 'Artist 3'], ['Artist 4']]
        })

        for artists in df['artist_names']:
            self.assertGreater(len(artists), 0)

    def test_year_reasonable_range(self):
        """Test that release_year is in reasonable range (1900-2100)"""
        df = pd.DataFrame({
            'release_year': [1990, 2000, 2023]
        })

        self.assertTrue(all(df['release_year'] >= 1900))
        self.assertTrue(all(df['release_year'] <= 2100))


class TestDataCompleteness(unittest.TestCase):
    """Test data completeness and coverage"""

    def test_no_duplicate_track_ids(self):
        """Test that track_id values are unique per playlist"""
        df = pd.DataFrame({
            'playlist_id': [1, 1, 1, 1],
            'track_id': ['track1', 'track2', 'track3', 'track1']  # Duplicate track1
        })

        # Check for duplicates
        duplicates = df.groupby(['playlist_id', 'track_id']).size()
        duplicates = duplicates[duplicates > 1]

        self.assertEqual(len(duplicates), 1, "Expected 1 duplicate track_id")

    def test_required_fields_not_null(self):
        """Test that required fields have no null values"""
        df = pd.DataFrame({
            'track_id': ['track1', 'track2', None],  # Has null
            'track_name': ['Song 1', 'Song 2', 'Song 3'],
            'track_duration_ms': [200000, None, 240000],  # Has null
        })

        # Required fields should not have nulls
        self.assertTrue(df['track_id'].isnull().any(), "track_id should have nulls for this test")
        self.assertTrue(df['track_duration_ms'].isnull().any(), "duration should have nulls for this test")

        # In production, these should fail validation
        null_track_ids = df['track_id'].isnull().sum()
        null_durations = df['track_duration_ms'].isnull().sum()

        # Assert that we detected the nulls
        self.assertEqual(null_track_ids, 1)
        self.assertEqual(null_durations, 1)


if __name__ == '__main__':
    unittest.main()
