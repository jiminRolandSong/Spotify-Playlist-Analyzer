from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Playlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    playlist_id = models.CharField(max_length=255)  # Unique identifier for the playlist
    playlist_url = models.URLField(max_length=200) # URL to the playlist
    playlist_name = models.CharField(max_length=255)
    playlist_owner = models.CharField(max_length=255)
    playlist_image = models.URLField(max_length=200, blank=True, null=True) # URL to the playlist image
    playlist_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'playlist_id') 

    def __str__(self):
        return self.playlist_name

class Track(models.Model):
    playlist = models.ForeignKey(Playlist, related_name='tracks', on_delete=models.CASCADE)
    track_id = models.CharField(max_length=255)
    track_name = models.CharField(max_length=255)
    track_duration_ms = models.IntegerField()
    track_popularity = models.IntegerField(null=True, blank=True)
    track_genres = models.JSONField(default=list)  # Store genres as a list
    album_id = models.CharField(max_length=255)
    album_name = models.CharField(max_length=255)
    album_release_date = models.DateField(null=True, blank=True)
    album_label = models.CharField(max_length=255, null=True, blank=True)
    artist_ids = models.JSONField(default=list)  # Store artist IDs as a list
    artist_names = models.JSONField(default=list)  # Store artist names as a list

    def __str__(self):
        return self.track_name