"""Music views."""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.http import HttpResponse, Http404, FileResponse
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter, OpenApiExample
from apps.common.permissions import IsAdminOnly
from apps.common.utils import get_client_ip
from .models import Track, Playlist, PlaylistTrack, PlayHistory, MusicSettings
from .serializers import (
    TrackSerializer, TrackUploadSerializer, TrackListSerializer,
    PlaylistSerializer, PlayHistorySerializer, MusicSettingsSerializer,
    TrackReorderSerializer, FeaturedTrackSerializer
)


class TrackListView(generics.ListAPIView):
    """
    List all tracks.

    Returns a list of all available tracks with featured tracks appearing first.
    """
    serializer_class = TrackListSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Tracks'],
        summary="List all tracks",
        description="Returns a list of all available tracks with featured tracks appearing first.",
        responses={
            200: TrackListSerializer(many=True),
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Track.objects.filter(is_deleted=False)
        queryset = queryset.order_by(
            '-is_featured', 'sort_order', '-created_at')
        return queryset


class TrackDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific track.

    Returns detailed information about a specific track including metadata and streaming URLs.
    """
    queryset = Track.objects.filter(is_deleted=False)
    serializer_class = TrackSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Tracks'],
        summary="Get track details",
        description="Returns detailed information about a specific track.",
        responses={
            200: TrackSerializer,
            404: OpenApiResponse(description="Track not found")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class TrackUploadView(generics.CreateAPIView):
    """
    Upload a new track.

    Upload a new audio track (Admin only).
    """
    serializer_class = TrackUploadSerializer
    permission_classes = [IsAdminOnly]

    @extend_schema(
        tags=['Music - Tracks'],
        summary="Upload new track",
        description="Upload a new audio track (Admin only).",
        request=TrackUploadSerializer,
        responses={
            201: TrackSerializer,
            400: OpenApiResponse(description="Invalid input"),
            403: OpenApiResponse(description="Permission denied")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class TrackManageView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a track.

    Manage track details (Admin only).
    """
    queryset = Track.objects.filter(is_deleted=False)
    serializer_class = TrackSerializer
    permission_classes = [IsAdminOnly]

    @extend_schema(
        tags=['Music - Tracks'],
        summary="Get track details",
        description="Retrieve track details (Admin only).",
        responses={
            200: TrackSerializer,
            404: OpenApiResponse(description="Track not found")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Music - Tracks'],
        summary="Update track",
        description="Update track details (Admin only).",
        request=TrackSerializer,
        responses={
            200: TrackSerializer,
            400: OpenApiResponse(description="Invalid input"),
            404: OpenApiResponse(description="Track not found")
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        tags=['Music - Tracks'],
        summary="Partial update track",
        description="Partially update track details (Admin only).",
        request=TrackSerializer,
        responses={
            200: TrackSerializer,
            400: OpenApiResponse(description="Invalid input"),
            404: OpenApiResponse(description="Track not found")
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=['Music - Tracks'],
        summary="Delete track",
        description="Soft delete a track (Admin only).",
        responses={
            204: OpenApiResponse(description="Track deleted successfully"),
            404: OpenApiResponse(description="Track not found")
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # Soft delete
        instance.delete()


@extend_schema(
    tags=['Tracks'],
    summary="Stream audio track",
    description="Streams an audio file with support for HTTP range requests for efficient audio streaming.",
    responses={
        200: OpenApiResponse(description="Audio stream", response=bytes),
        206: OpenApiResponse(description="Partial content", response=bytes),
        404: OpenApiResponse(description="Track not found"),
        416: OpenApiResponse(description="Range not satisfiable")
    },
    parameters=[
        OpenApiParameter(
            name='track_id',
            location=OpenApiParameter.PATH,
            description='ID of the track to stream',
            type=int
        )
    ]
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def stream_track(request, track_id):
    """
    Stream audio track with range request support.
    """
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


@extend_schema(
    tags=['Tracks'],
    summary="Get current featured track",
    description="Returns the currently featured track, if one is set.",
    responses={
        200: TrackListSerializer,
        204: OpenApiResponse(description="No featured track set")
    }
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def current_featured(request):
    """
    Get current featured track.
    """
    featured_track = Track.get_featured_track()
    if featured_track:
        serializer = TrackListSerializer(
            featured_track, context={'request': request})
        return Response(serializer.data)
    return Response(None, status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=['Music - Tracks'],
    summary="Set featured track",
    description="Sets the specified track as the featured track and removes featured status from all other tracks.",
    request=FeaturedTrackSerializer,
    responses={
        200: OpenApiResponse(description="Track set as featured"),
        400: OpenApiResponse(description="Invalid input"),
        404: OpenApiResponse(description="Track not found"),
        403: OpenApiResponse(description="Permission denied")
    },
    parameters=[
        OpenApiParameter(
            name='track_id',
            location=OpenApiParameter.PATH,
            description='ID of the track to set as featured',
            type=int
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAdminOnly])
def set_featured(request, track_id):
    """
    Set a track as featured.
    """
    serializer = FeaturedTrackSerializer(data={'track_id': track_id})
    serializer.is_valid(raise_exception=True)

    # Remove featured status from all tracks
    Track.objects.filter(is_featured=True).update(is_featured=False)

    # Set new featured track
    track = Track.objects.get(id=track_id)
    track.is_featured = True
    track.save(update_fields=['is_featured'])

    return Response({'message': f'Track "{track.title}" set as featured.'})


@extend_schema(
    tags=['Music - Tracks'],
    summary="Reorder tracks",
    description="Updates the sort order of tracks based on the provided list of track IDs.",
    request=TrackReorderSerializer,
    responses={
        200: OpenApiResponse(description="Tracks reordered successfully"),
        400: OpenApiResponse(description="Invalid input"),
        403: OpenApiResponse(description="Permission denied")
    }
)
@api_view(['POST'])
@permission_classes([IsAdminOnly])
def reorder_tracks(request):
    """
    Reorder tracks.
    """
    serializer = TrackReorderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    track_ids = serializer.validated_data['track_ids']  # type: ignore

    # Update sort order
    with transaction.atomic():
        for index, track_id in enumerate(track_ids):
            Track.objects.filter(id=track_id).update(sort_order=index)

    return Response({'message': 'Tracks reordered successfully.'})


@extend_schema(
    tags=['Music - Tracks'],
    summary="Delete track",
    description="Soft deletes the specified track (Admin only).",
    responses={
        200: OpenApiResponse(description="Track deleted successfully"),
        404: OpenApiResponse(description="Track not found"),
        403: OpenApiResponse(description="Permission denied")
    },
    parameters=[
        OpenApiParameter(
            name='track_id',
            location=OpenApiParameter.PATH,
            description='ID of the track to delete',
            type=int
        )
    ]
)
@api_view(['DELETE'])
@permission_classes([IsAdminOnly])
def delete_track(request, track_id):
    """
    Delete a track.
    """
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
    """
    List and create playlists.
    """
    serializer_class = PlaylistSerializer
    permission_classes = [IsAdminOnly]

    @extend_schema(
        tags=['Music - Playlists'],
        summary="List playlists",
        description="Returns a list of all playlists (Admin only).",
        responses={
            200: PlaylistSerializer(many=True),
            403: OpenApiResponse(description="Permission denied")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Music - Playlists'],
        summary="Create playlist",
        description="Creates a new playlist (Admin only).",
        request=PlaylistSerializer,
        responses={
            201: PlaylistSerializer,
            400: OpenApiResponse(description="Invalid input"),
            403: OpenApiResponse(description="Permission denied")
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        return Playlist.objects.filter(is_deleted=False).order_by('sort_order')


class PlaylistDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Playlist detail view.
    """
    queryset = Playlist.objects.filter(is_deleted=False)
    serializer_class = PlaylistSerializer
    permission_classes = [IsAdminOnly]

    @extend_schema(
        tags=['Music - Playlists'],
        summary="Get playlist details",
        description="Retrieve playlist details (Admin only).",
        responses={
            200: PlaylistSerializer,
            404: OpenApiResponse(description="Playlist not found"),
            403: OpenApiResponse(description="Permission denied")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Music - Playlists'],
        summary="Update playlist",
        description="Update playlist details (Admin only).",
        request=PlaylistSerializer,
        responses={
            200: PlaylistSerializer,
            400: OpenApiResponse(description="Invalid input"),
            404: OpenApiResponse(description="Playlist not found"),
            403: OpenApiResponse(description="Permission denied")
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        tags=['Music - Playlists'],
        summary="Partial update playlist",
        description="Partially update playlist details (Admin only).",
        request=PlaylistSerializer,
        responses={
            200: PlaylistSerializer,
            400: OpenApiResponse(description="Invalid input"),
            404: OpenApiResponse(description="Playlist not found"),
            403: OpenApiResponse(description="Permission denied")
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        tags=['Music - Playlists'],
        summary="Delete playlist",
        description="Delete a playlist (Admin only).",
        responses={
            204: OpenApiResponse(description="Playlist deleted successfully"),
            404: OpenApiResponse(description="Playlist not found"),
            403: OpenApiResponse(description="Permission denied")
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


@extend_schema(
    tags=['Music - Playlists'],
    summary="Add track to playlist",
    description="Adds the specified track to the specified playlist.",
    responses={
        200: OpenApiResponse(description="Track added to playlist"),
        400: OpenApiResponse(description="Track already in playlist"),
        404: OpenApiResponse(description="Playlist or track not found"),
        403: OpenApiResponse(description="Permission denied")
    },
    parameters=[
        OpenApiParameter(
            name='playlist_id',
            location=OpenApiParameter.PATH,
            description='ID of the playlist',
            type=int
        ),
        OpenApiParameter(
            name='track_id',
            location=OpenApiParameter.PATH,
            description='ID of the track to add',
            type=int
        )
    ]
)
@api_view(['POST'])
@permission_classes([IsAdminOnly])
def add_track_to_playlist(request, playlist_id, track_id):
    """
    Add a track to a playlist.
    """
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


@extend_schema(
    tags=['Music - Playlists'],
    summary="Remove track from playlist",
    description="Removes the specified track from the specified playlist.",
    responses={
        200: OpenApiResponse(description="Track removed from playlist"),
        404: OpenApiResponse(description="Track not in playlist"),
        403: OpenApiResponse(description="Permission denied")
    },
    parameters=[
        OpenApiParameter(
            name='playlist_id',
            location=OpenApiParameter.PATH,
            description='ID of the playlist',
            type=int
        ),
        OpenApiParameter(
            name='track_id',
            location=OpenApiParameter.PATH,
            description='ID of the track to remove',
            type=int
        )
    ]
)
@api_view(['DELETE'])
@permission_classes([IsAdminOnly])
def remove_track_from_playlist(request, playlist_id, track_id):
    """
    Remove a track from a playlist.
    """
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
    """
    User's play history.
    """
    serializer_class = PlayHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Music History'],
        summary="Get play history",
        description="Returns the authenticated user's play history, ordered by most recent plays first.",
        responses={
            200: PlayHistorySerializer(many=True),
            401: OpenApiResponse(description="Authentication required")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return PlayHistory.objects.filter(
            user=self.request.user
        ).select_related('track')


@extend_schema(
    tags=['Music History'],
    summary="Log track play",
    description="Logs that a track was played. Can be used by both authenticated and anonymous users.",
    request=None,
    responses={
        200: OpenApiResponse(description="Play logged successfully"),
        404: OpenApiResponse(description="Track not found")
    },
    parameters=[
        OpenApiParameter(
            name='track_id',
            location=OpenApiParameter.PATH,
            description='ID of the track that was played',
            type=int
        )
    ],
    examples=[
        OpenApiExample(
            'Example request',
            value={
                'duration_played': 120,
                'completed': True
            },
            request_only=True
        )
    ]
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def log_play(request, track_id):
    """
    Log track play.
    """
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
    """
    Music settings management.
    """
    serializer_class = MusicSettingsSerializer
    permission_classes = [IsAdminOnly]

    @extend_schema(
        tags=['Music - Settings'],
        summary="Get music settings",
        description="Returns current music settings (Admin only).",
        responses={
            200: MusicSettingsSerializer,
            403: OpenApiResponse(description="Permission denied")
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        tags=['Music - Settings'],
        summary="Update music settings",
        description="Updates music settings (Admin only).",
        request=MusicSettingsSerializer,
        responses={
            200: MusicSettingsSerializer,
            400: OpenApiResponse(description="Invalid input"),
            403: OpenApiResponse(description="Permission denied")
        }
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        tags=['Music - Settings'],
        summary="Partial update music settings",
        description="Partially updates music settings (Admin only).",
        request=MusicSettingsSerializer,
        responses={
            200: MusicSettingsSerializer,
            400: OpenApiResponse(description="Invalid input"),
            403: OpenApiResponse(description="Permission denied")
        }
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        return MusicSettings.get_settings()


@extend_schema(
    tags=['Statistics'],
    summary="Get music statistics",
    description="Returns overall music statistics including total tracks, total plays, featured track, and popular tracks.",
    responses={
        200: OpenApiResponse(
            description="Music statistics",
            examples=[
                OpenApiExample(
                    'Example response',
                    value={
                        'total_tracks': 42,
                        'total_plays': 1500,
                        'featured_track': {
                            'id': 1,
                            'title': 'Featured Song',
                            'artist': 'Featured Artist',
                            'duration': 180,
                            'formatted_duration': '03:00',
                            'is_featured': True,
                            'genre': 'Rock',
                            'play_count': 500
                        },
                        'popular_tracks': [
                            {
                                'id': 1,
                                'title': 'Popular Song 1',
                                'artist': 'Artist 1',
                                'duration': 180,
                                'formatted_duration': '03:00',
                                'is_featured': False,
                                'genre': 'Pop',
                                'play_count': 300
                            }
                        ]
                    }
                )
            ]
        )
    }
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def music_stats(request):
    """
    Get music statistics.
    """
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
    """
    Helper function to log play history.
    """
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
