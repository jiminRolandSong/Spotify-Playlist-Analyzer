from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('analyze/', views.analyze_playlist, name='analyze_playlist'),
    path('dashboard/<str:playlist_id>/', views.dashboard, name='dashboard'),
    path('my-playlists/', views.user_playlists, name='user_playlists'),
]