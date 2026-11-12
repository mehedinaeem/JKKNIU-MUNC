from django.contrib import admin
from .models import EventAssignment
from .roles import is_super_admin


@admin.register(EventAssignment)
class EventAssignmentAdmin(admin.ModelAdmin):
    list_display = ['user', 'event', 'created_at']
    search_fields = ['user__username', 'event__title']
    autocomplete_fields = ['user', 'event']
    readonly_fields = ['created_at']

    def has_module_permission(self, request):
        return is_super_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_super_admin(request.user)

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission


# Role/assignment management must remain Super Admin-only even if an individual
# non-super administrator was accidentally granted direct auth model permissions.
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin


class SuperAdminOnlyMixin:
    def has_module_permission(self, request):
        return is_super_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return is_super_admin(request.user)

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset if is_super_admin(request.user) else queryset.none()


for model, base in ((get_user_model(), UserAdmin), (Group, GroupAdmin)):
    if admin.site.is_registered(model):
        admin.site.unregister(model)
    admin.site.register(model, type(f'SuperAdmin{base.__name__}', (SuperAdminOnlyMixin, base), {}))
