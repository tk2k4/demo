from whiteneuron.base.utils import base_badge_callback
from .models import *

def profileyoutube_badge_callback(request):
    return base_badge_callback(request, ProfileYoutube)

def playlistyoutube_badge_callback(request):
    return base_badge_callback(request, PlaylistYoutube)

def videoyoutube_badge_callback(request):
    return base_badge_callback(request, VideoYoutube)

