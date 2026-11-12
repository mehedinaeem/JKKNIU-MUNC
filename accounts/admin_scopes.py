from django.core.exceptions import PermissionDenied
from .roles import is_administrator, is_super_admin, is_event_manager, scope_queryset, can_manage_event, can_review_event


class EventScopedAdminMixin:
    """Scope both object pages and related-object widgets in the fallback admin."""
    event_path = 'event_id'
    review_model = False
    read_for_reviewers = False

    def get_queryset(self, request):
        return scope_queryset(super().get_queryset(request), request.user, self.event_path)

    def _allowed(self, request, obj=None, write=False):
        user = request.user
        if is_super_admin(user):
            return True
        role_ok = is_administrator(user) if self.review_model or (not write and self.read_for_reviewers) else is_event_manager(user)
        if not role_ok:
            return False
        if obj is None:
            return True
        event_id = obj
        for part in self.event_path.split('__'):
            event_id = getattr(event_id, part)
        return user.event_assignments.filter(event_id=event_id).exists()

    def has_module_permission(self, request):
        return self._allowed(request) and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return self._allowed(request, obj) and super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return self._allowed(request, obj, write=True) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._allowed(request, obj, write=True) and super().has_delete_permission(request, obj)

    def has_add_permission(self, request):
        return self._allowed(request, write=True) and super().has_add_permission(request)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        from events.models import Event
        from forms.models import RegistrationForm
        if db_field.name == 'event':
            kwargs['queryset'] = scope_queryset(Event.objects.all(), request.user, 'pk')
        elif db_field.name == 'form':
            kwargs['queryset'] = scope_queryset(RegistrationForm.objects.all(), request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not self._allowed(request, obj, write=True):
            raise PermissionDenied()
        super().save_model(request, obj, form, change)
