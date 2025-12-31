from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.views.generic import TemplateView
from whiteneuron.base.sites import base_admin_site

urlpatterns = []

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
else:
    # In production, static files are served by whitenoise
    urlpatterns += [
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
        path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT}),
    ]

# Define base urlpatterns
urlpatterns += [
    path("", include("whiteneuron.base.urls")),
    path("api/", include("whiteneuron.feedbacks.urls")),

    path("", include("apps.youtube.urls")),
]

if settings.UNFOLD['SHOW_LANGUAGES']:
    urlpatterns += [
        path("i18n/", include("django.conf.urls.i18n")),
        path("", base_admin_site.urls),
    ]
else:
    urlpatterns += [
        path("", base_admin_site.urls),
    ]