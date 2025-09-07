"""Music serializers."""

from rest_framework import serializers
from django.core.files.base import ContentFile
from apps.common.serializers import TimestampedSerializer
from .models import Track, Playlist, PlaylistTrack, PlayHistory, MusicSettings


class TrackSerializer(TimestampedSerializer):
    """Track serializer."""
    
    uploader_name = serializers.CharField(source='uploader.full_name', read_only=True)
    formatted_duration = serializers.CharField(read_only=True)
    stream_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Track
        fields = [
            'id', 'title', 'artist', 'file', 'cover_image', 'duration',
            'formatted_duration', 'is_featured', 'uploader_name',
            'genre', 'year', 'description', 'play_count', 'sort_order',
            'stream_url', 'cover_url', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'uploader_name', 'formatted_duration', 'play_count',
            'stream_url', 'cover_url', 'created_at', 'updated_at'
        ]

    def get_stream_url(self, obj):
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(f'/api/music/stream/{obj.id}/')
        return None

    def get_cover_url(self, obj):
        request = self.context.get('request')
        if request and obj.cover_image:
            return request.build_absolute_uri(obj.cover_image.url)
        return None

    def create(self, validated_data):
        validated_data['uploader'] = self.context['request'].user
        return super().create(validated_data)


class TrackUploadSerializer(serializers.ModelSerializer):
    """Track upload serializer with file validation."""
    
    class Meta:
        model = Track
        fields = [
            'title', 'artist', 'file', 'cover_image', 'duration',
            'genre', 'year', 'description'
        ]

    def validate_file(self, value):
        # Validate file type
        valid_extensions = ['.mp3', '.wav', '.ogg', '.m4a']
        import os
        ext = os.path.splitext(value.name)[1].lower()
        
        if ext not in valid_extensions:
            raise serializers.ValidationError(
                'Only MP3, WAV, OGG, and M4A files are allowed.'
            )
        
        # Validate file size (50MB max)
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError('File size cannot exceed 50MB.')
        
        return value

    def validate_duration(self, value):
        if value <= 0:
            raise serializers.ValidationError('Duration must be greater than 0.')
        if value > 3600:  # 1 hour max
            raise serializers.ValidationError('Track duration cannot exceed 1 hour.')
        return value

    def create(self, validated_data):
        validated_data['uploader'] = self.context['request'].user
        return super().create(validated_data)


class TrackListSerializer(serializers.ModelSerializer):
    """Minimal track serializer for lists."""
    
    formatted_duration = serializers.CharField(read_only=True)
    stream_url = serializers.SerializerMethodField()
    cover_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Track
        fields = [
            'id', 'title', 'artist', 'duration', 'formatted_duration',
            'is_featured', 'genre', 'play_count', 'stream_url', 'cover_url'
        ]

    def get_stream_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/music/stream/{obj.id}/')
        return None

    def get_cover_url(self, obj):
        request = self.context.get('request')
        if request and obj.cover_image:
            return request.build_absolute_uri(obj.cover_image.url)
        return None


class PlaylistTrackSerializer(serializers.ModelSerializer):
    """Playlist track serializer."""
    
    track = TrackListSerializer(read_only=True)
    
    class Meta:
        model = PlaylistTrack
        fields = ['id', 'track', 'sort_order', 'added_at']


class PlaylistSerializer(TimestampedSerializer):
    """Playlist serializer."""
    
    creator_name = serializers.CharField(source='creator.full_name', read_only=True)
    tracks = PlaylistTrackSerializer(source='playlisttrack_set', many=True, read_only=True)
    track_count = serializers.IntegerField(read_only=True)
    total_duration = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Playlist
        fields = [
            'id', 'name', 'description', 'creator_name', 'is_public',
            'cover_image', 'tracks', 'track_count', 'total_duration',
            'sort_order', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'creator_name', 'track_count', 'total_duration',
            'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        validated_data['creator'] = self.context['request'].user
        return super().create(validated_data)


class PlayHistorySerializer(serializers.ModelSerializer):
    """Play history serializer."""
    
    track_title = serializers.CharField(source='track.title', read_only=True)
    track_artist = serializers.CharField(source='track.artist', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = PlayHistory
        fields = [
            'id', 'track_title', 'track_artist', 'user_email',
            'played_at', 'duration_played', 'completed'
        ]
        read_only_fields = ['id', 'played_at']


class MusicSettingsSerializer(serializers.ModelSerializer):
    """Music settings serializer."""
    
    class Meta:
        model = MusicSettings
        fields = [
            'autoplay_enabled', 'default_volume', 'shuffle_enabled',
            'repeat_mode', 'crossfade_duration'
        ]

    def validate_default_volume(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError('Volume must be between 0 and 100.')
        return value

    def validate_crossfade_duration(self, value):
        if not 0 <= value <= 10:
            raise serializers.ValidationError('Crossfade duration must be between 0 and 10 seconds.')
        return value


class TrackReorderSerializer(serializers.Serializer):
    """Track reorder serializer."""
    
    track_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )

    def validate_track_ids(self, value):
        # Ensure all track IDs exist
        existing_count = Track.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError('Some track IDs are invalid.')
        
        # Ensure no duplicates
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Duplicate track IDs are not allowed.')
        
        return value


class FeaturedTrackSerializer(serializers.Serializer):
    """Featured track serializer."""
    
    track_id = serializers.IntegerField()

    def validate_track_id(self, value):
        try:
            Track.objects.get(id=value)
        except Track.DoesNotExist:
            raise serializers.ValidationError('Track not found.')
        return value