from django.db import models
from whiteneuron.base.models import BaseModel

# Create your models here.
class ProfileYoutube(BaseModel):
    gpm_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    raw_proxy = models.TextField(blank=True, null=True)
    profile_path = models.CharField(max_length=255)
    browser_type = models.CharField(max_length=255)
    browser_version = models.CharField(max_length=255)
    note = models.TextField(blank=True, null=True)
    profile_created_at = models.DateTimeField(auto_now_add=True)
    is_done = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Profile Youtube"
        verbose_name_plural = "Profiles Youtube"

    def __str__(self):
        return f"{self.name} ({self.gpm_id})"

class PlaylistYoutube(BaseModel):
    profile = models.ForeignKey(ProfileYoutube, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    youtube_link = models.CharField(max_length=10000)
    number_of_videos = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Playlist Youtube"
        verbose_name_plural = "Playlists Youtube"

    def __str__(self):
        return f"{self.name} - {self.profile.name}"

class VideoYoutube(BaseModel):
    playlist = models.ForeignKey(PlaylistYoutube, on_delete=models.CASCADE)
    youtube_link = models.CharField(max_length=10000)

    class Meta:
        verbose_name = "Video Youtube"
        verbose_name_plural = "Videos Youtube"

    def __str__(self):
        return f"{self.youtube_link[:50]}..." if len(self.youtube_link) > 50 else self.youtube_link



class ImportToolProxy(ProfileYoutube):
    class Meta:
        verbose_name = "Import Tool Proxy"
        verbose_name_plural = "Import Tools Proxy"
        proxy = True

class DashboardProxy(ProfileYoutube):
    class Meta:
        verbose_name = "ToolsDashboard"
        verbose_name_plural = "Tools Dashboards"
        proxy = True
