"""Music URLs."""

from django.urls import path
from . import views

urlpatterns = [
    # Public endpoints
    path('tracks/', views.TrackListView.as_view(), name='track_list'),
    path('tracks/<int:pk>/', views.TrackDetailView.as_view(), name='track_detail'),
    path('stream/<int:track_id>/', views.stream_track, name='stream_track'),
    path('current-featured/', views.current_featured, name='current_featured'),
    path('stats/', views.music_stats, name='music_stats'),
    
    # Play tracking
    path('play/<int:track_id>/', views.log_play, name='log_play'),
    path('history/', views.PlayHistoryView.as_view(), name='play_history'),
    
    # Admin endpoints
    path('admin/upload/', views.TrackUploadView.as_view(), name='track_upload'),
    path('admin/tracks/<int:pk>/', views.TrackManageView.as_view(), name='track_manage'),
    path('admin/tracks/<int:track_id>/delete/', views.delete_track, name='delete_track'),
    path('admin/featured/<int:track_id>/', views.set_featured, name='set_featured'),
    path('admin/reorder/', views.reorder_tracks, name='reorder_tracks'),
    
    # Playlists (Admin)
    path('admin/playlists/', views.PlaylistListCreateView.as_view(), name='playlist_list'),
    path('admin/playlists/<int:pk>/', views.PlaylistDetailView.as_view(), name='playlist_detail'),
    path('admin/playlists/<int:playlist_id>/tracks/<int:track_id>/', views.add_track_to_playlist, name='add_track_to_playlist'),
    path('admin/playlists/<int:playlist_id>/tracks/<int:track_id>/remove/', views.remove_track_from_playlist, name='remove_track_from_playlist'),
    
    # Settings (Admin)
    path('admin/settings/', views.MusicSettingsView.as_view(), name='music_settings'),
]