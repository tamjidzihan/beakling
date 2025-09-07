"""Music models."""

from django.db import models
from django.contrib.auth import get_user_model
from apps.common.models import BaseModel, OrderedModel
from apps.common.utils import validate_audio_file, validate_image_file

User = get_user_model()


class Track(BaseModel, OrderedModel):
    """Music track model."""

    title = models.CharField(max_length=255)
    artist = models.CharField(max_length=255, blank=True)
    file = models.FileField(
        upload_to='music/tracks/',
        validators=[validate_audio_file]
    )
    cover_image = models.ImageField(
        upload_to='music/covers/',
        null=True,
        blank=True,
        validators=[validate_image_file]
    )
    duration = models.PositiveIntegerField(help_text='Duration in seconds')
    is_featured = models.BooleanField(default=False)
    uploader = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_tracks'
    )

    # Metadata
    genre = models.CharField(max_length=100, blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True)

    # Play statistics
    play_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', '-created_at']
        indexes = [
            models.Index(fields=['is_featured', 'sort_order']),
            models.Index(fields=['uploader']),
        ]

    def __str__(self):
        artist_part = f" by {self.artist}" if self.artist else ""
        return f"{self.title}{artist_part}"

    def save(self, *args, **kwargs):
        # Ensure only one featured track at a time (optional)
        if self.is_featured:
            Track.objects.filter(is_featured=True).update(is_featured=False)
        super().save(*args, **kwargs)

    def increment_play_count(self):
        """Increment play count."""
        Track.objects.filter(id=self.id).update(  # type: ignore
            play_count=models.F('play_count') + 1)  # type: ignore

    @property
    def formatted_duration(self):
        """Get formatted duration (mm:ss)."""
        if self.duration is None:
            return "00:00"  # Or return an empty string if preferred
        minutes, seconds = divmod(self.duration, 60)
        return f"{minutes:02d}:{seconds:02d}"

    @classmethod
    def get_featured_track(cls):
        """Get the current featured track."""
        return cls.objects.filter(is_featured=True).first()


class Playlist(BaseModel, OrderedModel):
    """Playlist model."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='playlists'
    )
    tracks = models.ManyToManyField(
        Track,
        through='PlaylistTrack',
        related_name='playlists'
    )
    is_public = models.BooleanField(default=True)
    cover_image = models.ImageField(
        upload_to='music/playlist_covers/',
        null=True,
        blank=True,
        validators=[validate_image_file]
    )

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    @property
    def total_duration(self):
        """Get total playlist duration in seconds."""
        return self.tracks.aggregate(
            total=models.Sum('duration')
        )['total'] or 0

    @property
    def track_count(self):
        """Get number of tracks in playlist."""
        return self.tracks.count()


class PlaylistTrack(OrderedModel):
    """Through model for playlist tracks with ordering."""

    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['playlist', 'track']
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.playlist.name} - {self.track.title}"


class PlayHistory(models.Model):
    """Track play history."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='play_history'
    )
    track = models.ForeignKey(
        Track,
        on_delete=models.CASCADE,
        related_name='play_history'
    )
    played_at = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Playback details
    duration_played = models.PositiveIntegerField(
        default=0,
        help_text='Duration played in seconds'
    )
    completed = models.BooleanField(
        default=False,
        help_text='Whether the track was played to completion'
    )

    class Meta:
        ordering = ['-played_at']
        indexes = [
            models.Index(fields=['user', 'played_at']),
            models.Index(fields=['track', 'played_at']),
            models.Index(fields=['session_key']),
        ]

    def __str__(self):
        user_info = self.user.email if self.user else f"Anonymous ({self.session_key})"
        return f"{user_info} played {self.track.title}"


class MusicSettings(models.Model):
    """Global music settings."""

    autoplay_enabled = models.BooleanField(default=True)
    default_volume = models.PositiveIntegerField(
        default=70,
        help_text='Default volume (0-100)'
    )
    shuffle_enabled = models.BooleanField(default=False)
    repeat_mode = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Repeat'),
            ('one', 'Repeat One'),
            ('all', 'Repeat All'),
        ],
        default='none'
    )
    crossfade_duration = models.PositiveIntegerField(
        default=0,
        help_text='Crossfade duration in seconds'
    )

    class Meta:
        verbose_name = 'Music Settings'
        verbose_name_plural = 'Music Settings'

    def __str__(self):
        return "Music Settings"

    @classmethod
    def get_settings(cls):
        """Get or create music settings singleton."""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
