from django.urls import path
from . import views

app_name = "events"
urlpatterns = [
    path("events/", views.PublicEventList.as_view(), name="list"),
    path("events/<slug:slug>/", views.PublicEventDetail.as_view(), name="detail"),
    path("admin/events/", views.StaffEventCreate.as_view(), name="admin-create"),
    path("admin/events/<int:pk>/", views.StaffEventDetail.as_view(), name="admin-detail"),
]
