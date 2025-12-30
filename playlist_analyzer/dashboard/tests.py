"""
Django tests for the dashboard application
Tests models, views, and end-to-end workflows
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from unittest.mock import patch, Mock
import pandas as pd
from .models import Playlist, Track
from .views import load_tracks_to_db


class PlaylistModelTest(TestCase):
    """Test the Playlist model"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_create_playlist(self):
        """Test creating a playlist"""
        playlist = Playlist.objects.create(
            user=self.user,
            playlist_id='test123',
            playlist_url='https://open.spotify.com/playlist/test123',
            playlist_name='Test Playlist',
            playlist_owner='Test Owner'
        )

        self.assertEqual(playlist.playlist_name, 'Test Playlist')
        self.assertEqual(str(playlist), 'Test Playlist')

    def test_playlist_unique_together_constraint(self):
        """Test that user + playlist_id combination is unique"""
        Playlist.objects.create(
            user=self.user,
            playlist_id='test123',
            playlist_url='https://open.spotify.com/playlist/test123',
            playlist_name='Test Playlist',
            playlist_owner='Test Owner'
        )

        # Creating another playlist with same user and playlist_id should fail
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Playlist.objects.create(
                user=self.user,
                playlist_id='test123',  # Same playlist_id
                playlist_url='https://open.spotify.com/playlist/test123',
                playlist_name='Different Name',
                playlist_owner='Different Owner'
            )


class TrackModelTest(TestCase):
    """Test the Track model"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.playlist = Playlist.objects.create(
            user=self.user,
            playlist_id='test123',
            playlist_url='https://open.spotify.com/playlist/test123',
            playlist_name='Test Playlist',
            playlist_owner='Test Owner'
        )

    def test_create_track(self):
        """Test creating a track"""
        track = Track.objects.create(
            playlist=self.playlist,
            track_id='track123',
            track_name='Test Song',
            track_duration_ms=200000,
            track_popularity=80,
            track_genres=['pop', 'rock'],
            album_id='album123',
            album_name='Test Album',
            artist_ids=['artist1', 'artist2'],
            artist_names=['Artist 1', 'Artist 2']
        )

        self.assertEqual(track.track_name, 'Test Song')
        self.assertEqual(str(track), 'Test Song')
        self.assertIn('pop', track.track_genres)
        self.assertEqual(len(track.artist_names), 2)

    def test_track_unique_together_constraint(self):
        """Test that playlist + track_id combination is unique"""
        Track.objects.create(
            playlist=self.playlist,
            track_id='track123',
            track_name='Test Song',
            track_duration_ms=200000,
            track_popularity=80,
            track_genres=[],
            album_id='album123',
            album_name='Test Album',
            artist_ids=[],
            artist_names=[]
        )

        # Creating another track with same playlist and track_id should fail
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Track.objects.create(
                playlist=self.playlist,
                track_id='track123',  # Same track_id
                track_name='Different Song',
                track_duration_ms=300000,
                track_popularity=90,
                track_genres=[],
                album_id='album456',
                album_name='Different Album',
                artist_ids=[],
                artist_names=[]
            )


class LoadTracksToDBTest(TestCase):
    """Test the load_tracks_to_db function"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.playlist = Playlist.objects.create(
            user=self.user,
            playlist_id='test123',
            playlist_url='https://open.spotify.com/playlist/test123',
            playlist_name='Test Playlist',
            playlist_owner='Test Owner'
        )

    def test_load_new_tracks(self):
        """Test loading new tracks to database"""
        df = pd.DataFrame({
            'track_id': ['track1', 'track2'],
            'track_name': ['Song 1', 'Song 2'],
            'track_duration_ms': [200000, 180000],
            'track_popularity': [80, 75],
            'track_genres': [['pop'], ['rock', 'indie']],
            'album_id': ['album1', 'album2'],
            'album_name': ['Album 1', 'Album 2'],
            'album_release_date': [pd.to_datetime('2023-01-01'), pd.to_datetime('2023-02-01')],
            'album_label': ['Label 1', 'Label 2'],
            'artist_ids': [['artist1'], ['artist2', 'artist3']],
            'artist_names': [['Artist 1'], ['Artist 2', 'Artist 3']]
        })

        load_tracks_to_db(df, self.playlist)

        # Verify tracks were created
        tracks = Track.objects.filter(playlist=self.playlist)
        self.assertEqual(tracks.count(), 2)
        self.assertEqual(tracks.first().track_name, 'Song 1')

    def test_load_updates_existing_tracks(self):
        """Test that existing tracks are updated (UPSERT behavior)"""
        # Create initial track
        Track.objects.create(
            playlist=self.playlist,
            track_id='track1',
            track_name='Old Name',
            track_duration_ms=200000,
            track_popularity=50,
            track_genres=['old_genre'],
            album_id='album1',
            album_name='Old Album',
            artist_ids=['artist1'],
            artist_names=['Old Artist']
        )

        # Load updated data
        df = pd.DataFrame({
            'track_id': ['track1'],
            'track_name': ['New Name'],
            'track_duration_ms': [250000],
            'track_popularity': [90],
            'track_genres': [['new_genre']],
            'album_id': ['album1'],
            'album_name': ['New Album'],
            'album_release_date': [pd.to_datetime('2023-01-01')],
            'album_label': ['New Label'],
            'artist_ids': [['artist1']],
            'artist_names': [['New Artist']]
        })

        load_tracks_to_db(df, self.playlist)

        # Verify track was updated, not duplicated
        tracks = Track.objects.filter(playlist=self.playlist)
        self.assertEqual(tracks.count(), 1)  # Still only 1 track
        track = tracks.first()
        self.assertEqual(track.track_name, 'New Name')  # Updated
        self.assertEqual(track.track_popularity, 90)  # Updated


class DashboardViewsTest(TestCase):
    """Test Django views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.playlist = Playlist.objects.create(
            user=self.user,
            playlist_id='test123',
            playlist_url='https://open.spotify.com/playlist/test123',
            playlist_name='Test Playlist',
            playlist_owner='Test Owner'
        )
        # Add some tracks
        for i in range(3):
            Track.objects.create(
                playlist=self.playlist,
                track_id=f'track{i}',
                track_name=f'Song {i}',
                track_duration_ms=200000,
                track_popularity=80,
                track_genres=['pop', 'rock'],
                album_id=f'album{i}',
                album_name=f'Album {i}',
                artist_ids=[f'artist{i}'],
                artist_names=[f'Artist {i}']
            )

    def test_index_view(self):
        """Test the index page loads"""
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_authentication(self):
        """Test that dashboard view requires login"""
        response = self.client.get(
            reverse('dashboard:dashboard', args=['test123'])
        )
        # Should redirect or show error if not authenticated
        self.assertNotEqual(response.status_code, 200)

    def test_dashboard_view_authenticated(self):
        """Test dashboard view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('dashboard:dashboard', args=['test123'])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Playlist')
        self.assertIn('track_count', response.context)
        self.assertEqual(response.context['track_count'], 3)

    def test_user_playlists_view(self):
        """Test user playlists view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard:user_playlists'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('playlists', response.context)
        self.assertEqual(len(response.context['playlists']), 1)

    @patch('dashboard.views.spotify_api_setup')
    @patch('dashboard.views.extract_playlist_tracks')
    @patch('dashboard.views.transform_playlist_df')
    def test_analyze_playlist_view(self, mock_transform, mock_extract, mock_spotify):
        """Test playlist analysis workflow"""
        self.client.login(username='testuser', password='testpass123')

        # Mock the ETL functions
        mock_spotify.return_value = Mock()
        mock_extract.return_value = (
            pd.DataFrame({'track_id': ['track1']}),
            {'name': 'New Playlist', 'owner': 'Test Owner'}
        )
        mock_transform.return_value = pd.DataFrame({
            'track_id': ['track1'],
            'track_name': ['Test Song'],
            'track_duration_ms': [200000],
            'track_popularity': [80],
            'track_genres': [['pop']],
            'album_id': ['album1'],
            'album_name': ['Album'],
            'album_release_date': [pd.to_datetime('2023-01-01')],
            'album_label': ['Label'],
            'artist_ids': [['artist1']],
            'artist_names': [['Artist 1']]
        })

        response = self.client.post(
            reverse('dashboard:analyze_playlist'),
            {'url': 'https://open.spotify.com/playlist/newplaylist123'}
        )

        # Should redirect to dashboard after success
        self.assertEqual(response.status_code, 302)

        # Verify playlist was created
        playlist = Playlist.objects.get(playlist_id='newplaylist123')
        self.assertEqual(playlist.playlist_name, 'New Playlist')
