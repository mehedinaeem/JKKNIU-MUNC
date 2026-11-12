from rest_framework.permissions import BasePermission
from .roles import is_administrator, is_super_admin, is_event_manager


class IsAdministrator(BasePermission):
    message = 'An active administrator session is required.'

    def has_permission(self, request, view):
        return is_administrator(request.user)


class IsSuperAdmin(BasePermission):
    message = 'Super Admin access is required.'

    def has_permission(self, request, view):
        return is_super_admin(request.user)


class EventManagementPermission(BasePermission):
    message = 'Your role does not allow this administrative operation.'

    def has_permission(self, request, view):
        user = request.user
        if is_super_admin(user):
            return True
        action = {'GET': 'view', 'HEAD': 'view', 'OPTIONS': 'view', 'POST': 'add', 'DELETE': 'delete'}.get(request.method, 'change')
        if getattr(view, 'super_admin_create', False) and action == 'add':
            return False
        model = getattr(view, 'permission_model', 'club_forms.registrationform')
        action = getattr(view, 'permission_action', action)
        app_label, model_name = model.split('.')
        role_allowed = is_administrator(user) if model == 'events.event' and action == 'view' else is_event_manager(user)
        return role_allowed and user.has_perm(f'{app_label}.{action}_{model_name}')


class ApplicationReviewPermission(BasePermission):
    message = 'Assigned event application review access is required.'

    def has_permission(self, request, view):
        user = request.user
        if is_super_admin(user):
            return True
        action = 'change' if request.method == 'PATCH' else 'view'
        return is_administrator(user) and user.has_perm(f'registrations.{action}_formsubmission')
