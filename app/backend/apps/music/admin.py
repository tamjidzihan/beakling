"""Music admin configuration."""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Track, Playlist, PlaylistTrack, PlayHistory, MusicSettings


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    """Track admin configuration."""

    list_display = [
        'title', 'artist', 'formatted_duration', 'is_featured',
        'play_count', 'uploader', 'created_at', 'audio_player', 'sort_order'
    ]
    list_filter = ['is_featured', 'genre', 'uploader', 'created_at']
    search_fields = ['title', 'artist', 'genre']
    readonly_fields = ['play_count',
                       'created_at', 'updated_at']
    list_editable = ['is_featured', 'sort_order']

    fieldsets = (
        ('Track Information', {
            'fields': ('title', 'artist', 'file', 'cover_image', 'duration')
        }),
        ('Metadata', {
            'fields': ('genre', 'year', 'description')
        }),
        ('Settings', {
            'fields': ('is_featured', 'sort_order', 'uploader')
        }),
        ('Statistics', {
            'fields': (['play_count']),
            'classes': ('collapse')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse')
        }),
    )

    def audio_player(self, obj):
        if obj.file:
            return format_html(
                '<audio controls preload="none" style="width: 200px;">'
                '<source src="{}" type="audio/mpeg">'
                'Your browser does not support the audio element.'
                '</audio>',
                obj.file.url
            )
        return "No audio file"
    audio_player.short_description = 'Player'

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.uploader = request.user
        super().save_model(request, obj, form, change)

    actions = ['set_as_featured', 'remove_featured']

    def set_as_featured(self, request, queryset):
        # Remove featured from all tracks
        Track.objects.update(is_featured=False)
        # Set first selected track as featured
        if queryset.exists():
            track = queryset.first()
            track.is_featured = True
            track.save()
            self.message_user(
                request, f'"{track.title}" set as featured track.')
    set_as_featured.short_description = 'Set as featured track'

    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(
            request, 'Removed featured status from selected tracks.')
    remove_featured.short_description = 'Remove featured status'


class PlaylistTrackInline(admin.TabularInline):
    """Playlist track inline."""
    model = PlaylistTrack
    extra = 0
    fields = ['track', 'sort_order']
    autocomplete_fields = ['track']


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    """Playlist admin configuration."""

    list_display = ['name', 'creator', 'track_count',
                    'total_duration_display', 'is_public', 'created_at']
    list_filter = ['is_public', 'creator', 'created_at']
    search_fields = ['name', 'description', 'creator__email']
    inlines = [PlaylistTrackInline]

    fieldsets = (
        ('Playlist Information', {
            'fields': ('name', 'description', 'cover_image')
        }),
        ('Settings', {
            'fields': ('creator', 'is_public', 'sort_order')
        }),
        ('Statistics', {
            'fields': ('track_count', 'total_duration'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['track_count', 'total_duration']

    def total_duration_display(self, obj):
        total_seconds = obj.total_duration
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
    total_duration_display.short_description = 'Total Duration'

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.creator = request.user
        super().save_model(request, obj, form, change)


@admin.register(PlayHistory)
class PlayHistoryAdmin(admin.ModelAdmin):
    """Play history admin configuration."""

    list_display = ['track_title', 'user_email',
                    'played_at', 'duration_played', 'completed']
    list_filter = ['completed', 'played_at', 'track']
    search_fields = ['track__title', 'user__email']
    readonly_fields = ['played_at']

    def track_title(self, obj):
        return obj.track.title
    track_title.short_description = 'Track'

    def user_email(self, obj):
        return obj.user.email if obj.user else f"Anonymous ({obj.session_key[:8]}...)"
    user_email.short_description = 'User'

    def has_add_permission(self, request):
        return False  # Disable manual creation

    def has_change_permission(self, request, obj=None):
        return False  # Disable editing


@admin.register(MusicSettings)
class MusicSettingsAdmin(admin.ModelAdmin):
    """Music settings admin configuration."""

    list_display = ['autoplay_enabled', 'default_volume',
                    'shuffle_enabled', 'repeat_mode']

    fieldsets = (
        ('Playback Settings', {
            'fields': ('autoplay_enabled', 'default_volume', 'shuffle_enabled', 'repeat_mode')
        }),
        ('Advanced Settings', {
            'fields': ('crossfade_duration',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # Only allow one settings instance
        return not MusicSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False  # Don't allow deletion
