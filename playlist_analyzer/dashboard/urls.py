from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('analyze/', views.analyze_playlist, name='analyze_playlist'),
    path('dashboard/<str:playlist_id>/', views.dashboard, name='dashboard'),
]