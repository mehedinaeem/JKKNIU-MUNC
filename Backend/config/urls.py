from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/", include("membership.urls")),
    path("admin/", admin.site.urls),
    path("api/", include("config.health.urls")),
    path("api/", include("accounts.urls")),
    path("api/", include("events.urls")),
    path("api/", include("forms.urls")),
    path("api/", include("registrations.urls")),
    path("api/", include("mailing.urls")),
]
