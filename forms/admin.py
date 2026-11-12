from django.contrib import admin
from .models import RegistrationForm


@admin.register(RegistrationForm)
class RegistrationFormAdmin(admin.ModelAdmin):
    list_display = ["title", "event", "form_type", "status", "capacity", "opens_at", "closes_at"]
    list_filter = ["status", "form_type"]
    search_fields = ["title", "slug", "event__title"]
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["event"]
    readonly_fields = ["created_at", "updated_at"]
