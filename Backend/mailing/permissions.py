from rest_framework.permissions import BasePermission
from rest_framework.throttling import UserRateThrottle
from accounts.roles import is_event_manager, is_super_admin


class EmailPermission(BasePermission):
    message = 'Email management requires Event Admin or Super Admin access.'
    def has_permission(self, request, view):
        return is_event_manager(request.user) and (is_super_admin(request.user) or request.user.has_perm('events.change_event'))


class EmailThrottle(UserRateThrottle):
    scope = 'email_admin'
    rate = '120/min'
