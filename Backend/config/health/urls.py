from django.urls import path
from .views import HealthView

app_name = "health"
urlpatterns = [path("health/", HealthView.as_view(), name="health")]
