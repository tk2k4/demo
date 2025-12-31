from django.contrib import admin
from .models import ProfileYoutube, PlaylistYoutube, VideoYoutube, ImportToolProxy, DashboardProxy
from whiteneuron.base.admin import ModelAdmin, base_admin_site, TabularInline

# Register your models here.


class PlaylistYoutubeInline(TabularInline):
    model = PlaylistYoutube
    tab = True
    extra = 1
    fields = ('name', 'youtube_link', 'number_of_videos')
    verbose_name = "Playlist"
    verbose_name_plural = "Playlists"
    readonly_fields = ('youtube_link','name','number_of_videos')

    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ProfileYoutube, site=base_admin_site)
class ProfileYoutubeAdmin(ModelAdmin):
    list_display = ['gpm_id', 'name', 'browser_type', 'browser_version', 'is_done', 'profile_created_at']
    search_fields = ['gpm_id', 'name', 'note']
    list_filter = ['is_done', 'browser_type', 'browser_version', 'profile_created_at']
    readonly_fields = ['profile_created_at']
    change_list_template = 'youtube/profileyoutube_changelist.html'
    change_form_template = 'youtube/profileyoutube_change_form.html'
    inlines = [PlaylistYoutubeInline]

    fieldsets = (
        ('Cơ bản', {
            'fields': ('gpm_id', 'name', 'profile_path', 'browser_type', 'browser_version', 'is_done')
        }),
        ('Chi tiết', {
            'fields': ('raw_proxy', 'note', 'profile_created_at')
        }),
    )

@admin.register(PlaylistYoutube, site=base_admin_site)
class PlaylistYoutubeAdmin(ModelAdmin):
    list_display = ['name', 'profile', 'youtube_link']
    search_fields = ['name', 'youtube_link', 'profile__name', 'profile__gpm_id']
    list_filter = ['profile']
    autocomplete_fields = ['profile']
    readonly_fields = ['youtube_link','name','profile','number_of_videos']
    fieldsets = (
        ('Cơ bản', {
            'fields': ('profile', 'name', 'youtube_link', 'number_of_videos')
        }),
    )

@admin.register(VideoYoutube, site=base_admin_site)
class VideoYoutubeAdmin(ModelAdmin):
    list_display = ['youtube_link', 'playlist', 'created_at']
    search_fields = ['youtube_link', 'playlist__name', 'playlist__profile__name']
    list_filter = ['playlist', 'created_at']
    autocomplete_fields = ['playlist']

    fieldsets = (
        ('Cơ bản', {
            'fields': ('playlist', 'youtube_link')
        }),
    )


@admin.register(ImportToolProxy, site=base_admin_site)
class ImportToolProxyAdmin(ModelAdmin):
    change_list_template = 'youtube/importtoolproxy_changelist.html'


@admin.register(DashboardProxy, site=base_admin_site)
class DashboardProxyAdmin(ModelAdmin):
    change_list_template = 'youtube/dashboardproxy_changelist.html'
    default_toggle_sidebar = False

