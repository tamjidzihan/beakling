"""Music views."""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.http import HttpResponse, Http404, FileResponse
from django.db import transaction
from django.utils import timezone
from apps.common.permissions import IsAdminOnly
from apps.common.utils import get_client_ip
from .models import Track, Playlist, PlaylistTrack, PlayHistory, MusicSettings
from .serializers import (
    TrackSerializer, TrackUploadSerializer, TrackListSerializer,
    PlaylistSerializer, PlayHistorySerializer, MusicSettingsSerializer,
    TrackReorderSerializer, FeaturedTrackSerializer
)


class TrackListView(generics.ListAPIView):
    """List all tracks."""
    serializer_class = TrackListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Track.objects.filter(is_deleted=False)

        # Featured tracks first
        queryset = queryset.order_by(
            '-is_featured', 'sort_order', '-created_at')

        return queryset


class TrackDetailView(generics.RetrieveAPIView):
    """Track detail view."""
    queryset = Track.objects.filter(is_deleted=False)
    serializer_class = TrackSerializer
    permission_classes = [permissions.AllowAny]


class TrackUploadView(generics.CreateAPIView):
    """Upload new track (Admin only)."""
    serializer_class = TrackUploadSerializer
    permission_classes = [IsAdminOnly]


class TrackManageView(generics.RetrieveUpdateDestroyAPIView):
    """Manage track (Admin only)."""
    queryset = Track.objects.filter(is_deleted=False)
    serializer_class = TrackSerializer
    permission_classes = [IsAdminOnly]

    def perform_destroy(self, instance):
        # Soft delete
        instance.delete()


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def stream_track(request, track_id):
    """Stream audio track with range request support."""
    try:
        track = Track.objects.get(id=track_id, is_deleted=False)
    except Track.DoesNotExist:
        raise Http404("Track not found")

    # Log play history
    log_play_history(request, track)

    # Get file path
    file_path = track.file.path

    try:
        # Handle range requests for audio streaming
        range_header = request.META.get('HTTP_RANGE', '').strip()

        if range_header:
            # Parse range header
            range_match = range_header.replace('bytes=', '').split('-')
            start = int(range_match[0]) if range_match[0] else 0
            end = int(range_match[1]) if range_match[1] else None

            # Get file size
            import os
            file_size = os.path.getsize(file_path)

            if end is None:
                end = file_size - 1

            # Validate range
            if start >= file_size or end >= file_size:
                response = HttpResponse(status=416)  # Range Not Satisfiable
                response['Content-Range'] = f'bytes */{file_size}'
                return response

            # Create partial response
            with open(file_path, 'rb') as f:
                f.seek(start)
                data = f.read(end - start + 1)

            response = HttpResponse(
                data,
                status=206,  # Partial Content
                content_type='audio/mpeg'
            )
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Accept-Ranges'] = 'bytes'
            response['Content-Length'] = str(end - start + 1)

        else:
            # Regular file response
            response = FileResponse(
                open(file_path, 'rb'),
                content_type='audio/mpeg'
            )
            response['Accept-Ranges'] = 'bytes'

        # Add cache headers
        response['Cache-Control'] = 'public, max-age=3600'
        return response

    except FileNotFoundError:
        raise Http404("Audio file not found")


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def current_featured(request):
    """Get current featured track."""
    featured_track = Track.get_featured_track()
    if featured_track:
        serializer = TrackListSerializer(
            featured_track, context={'request': request})
        return Response(serializer.data)
    return Response(None)


@api_view(['POST'])
@permission_classes([IsAdminOnly])
def set_featured(request, track_id):
    """Set track as featured."""
    serializer = FeaturedTrackSerializer(data={'track_id': track_id})
    serializer.is_valid(raise_exception=True)

    # Remove featured status from all tracks
    Track.objects.filter(is_featured=True).update(is_featured=False)

    # Set new featured track
    track = Track.objects.get(id=track_id)
    track.is_featured = True
    track.save(update_fields=['is_featured'])

    return Response({'message': f'Track "{track.title}" set as featured.'})


@api_view(['POST'])
@permission_classes([IsAdminOnly])
def reorder_tracks(request):
    """Reorder tracks."""
    serializer = TrackReorderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    track_ids = serializer.validated_data['track_ids']  # type: ignore

    # Update sort order
    with transaction.atomic():
        for index, track_id in enumerate(track_ids):
            Track.objects.filter(id=track_id).update(sort_order=index)

    return Response({'message': 'Tracks reordered successfully.'})


@api_view(['DELETE'])
@permission_classes([IsAdminOnly])
def delete_track(request, track_id):
    """Delete track (Admin only)."""
    try:
        track = Track.objects.get(id=track_id)
        track_title = track.title

        # Soft delete
        track.delete()

        return Response({
            'message': f'Track "{track_title}" deleted successfully.'
        })

    except Track.DoesNotExist:
        return Response(
            {'error': 'Track not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


class PlaylistListCreateView(generics.ListCreateAPIView):
    """List and create playlists."""
    serializer_class = PlaylistSerializer
    permission_classes = [IsAdminOnly]

    def get_queryset(self):
        return Playlist.objects.filter(is_deleted=False).order_by('sort_order')


class PlaylistDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Playlist detail view."""
    queryset = Playlist.objects.filter(is_deleted=False)
    serializer_class = PlaylistSerializer
    permission_classes = [IsAdminOnly]


@api_view(['POST'])
@permission_classes([IsAdminOnly])
def add_track_to_playlist(request, playlist_id, track_id):
    """Add track to playlist."""
    try:
        playlist = Playlist.objects.get(id=playlist_id)
        track = Track.objects.get(id=track_id)

        playlist_track, created = PlaylistTrack.objects.get_or_create(
            playlist=playlist,
            track=track,
            defaults={'sort_order': playlist.tracks.count()}
        )

        if created:
            return Response({'message': f'Track added to "{playlist.name}".'})
        else:
            return Response({'message': 'Track already in playlist.'})

    except (Playlist.DoesNotExist, Track.DoesNotExist):
        return Response(
            {'error': 'Playlist or track not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['DELETE'])
@permission_classes([IsAdminOnly])
def remove_track_from_playlist(request, playlist_id, track_id):
    """Remove track from playlist."""
    try:
        playlist_track = PlaylistTrack.objects.get(
            playlist_id=playlist_id,
            track_id=track_id
        )
        playlist_track.delete()

        return Response({'message': 'Track removed from playlist.'})

    except PlaylistTrack.DoesNotExist:
        return Response(
            {'error': 'Track not in playlist.'},
            status=status.HTTP_404_NOT_FOUND
        )


class PlayHistoryView(generics.ListAPIView):
    """User's play history."""
    serializer_class = PlayHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PlayHistory.objects.filter(
            user=self.request.user
        ).select_related('track')


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def log_play(request, track_id):
    """Log track play."""
    try:
        track = Track.objects.get(id=track_id, is_deleted=False)
        log_play_history(request, track, request.data)

        return Response({'message': 'Play logged.'})

    except Track.DoesNotExist:
        return Response(
            {'error': 'Track not found.'},
            status=status.HTTP_404_NOT_FOUND
        )


class MusicSettingsView(generics.RetrieveUpdateAPIView):
    """Music settings management (Admin only)."""
    serializer_class = MusicSettingsSerializer
    permission_classes = [IsAdminOnly]

    def get_object(self):
        return MusicSettings.get_settings()


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def music_stats(request):
    """Get music statistics."""
    stats = {
        'total_tracks': Track.objects.filter(is_deleted=False).count(),
        'total_plays': PlayHistory.objects.count(),
        'featured_track': None,
        'popular_tracks': []
    }

    # Featured track
    featured = Track.get_featured_track()
    if featured:
        stats['featured_track'] = TrackListSerializer(
            featured, context={'request': request}
        ).data

    # Popular tracks (most played)
    popular_tracks = Track.objects.filter(
        is_deleted=False
    ).order_by('-play_count')[:5]

    stats['popular_tracks'] = TrackListSerializer(
        popular_tracks, many=True, context={'request': request}
    ).data

    return Response(stats)


def log_play_history(request, track, play_data=None):
    """Helper function to log play history."""
    if play_data is None:
        play_data = {}

    # Increment play count
    track.increment_play_count()

    # Log play history
    history_data = {
        'track': track,
        'ip_address': get_client_ip(request),
        'duration_played': play_data.get('duration_played', 0),
        'completed': play_data.get('completed', False)
    }

    if request.user.is_authenticated:
        history_data['user'] = request.user
    else:
        if not request.session.session_key:
            request.session.create()
        history_data['session_key'] = request.session.session_key

    PlayHistory.objects.create(**history_data)
