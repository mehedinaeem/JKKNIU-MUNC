from django.contrib import admin
from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "event_type", "status", "start_date", "organizer"]
    list_filter = ["status", "event_type"]
    search_fields = ["title", "description", "venue"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["organizer"]
