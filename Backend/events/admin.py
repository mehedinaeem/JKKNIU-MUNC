from accounts.admin_scopes import EventScopedAdminMixin
from accounts.roles import is_super_admin
from django.contrib import admin
from .models import Event


@admin.register(Event)
class EventAdmin(EventScopedAdminMixin, admin.ModelAdmin):
    event_path = 'pk'
    read_for_reviewers = True

    def has_add_permission(self, request):
        return is_super_admin(request.user)

    def get_readonly_fields(self, request, obj=None):
        return list(self.readonly_fields) + ([] if is_super_admin(request.user) else ['organizer'])

    list_display = ["title", "event_type", "status", "start_date", "organizer"]
    list_filter = ["status", "event_type"]
    search_fields = ["title", "description", "venue"]
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["organizer"]
