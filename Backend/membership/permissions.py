from rest_framework.permissions import BasePermission
from accounts.roles import active_staff, is_super_admin


def can_manage_members(user):
    return is_super_admin(user) or (active_staff(user) and user.has_perm('membership.manage_membership'))


class MembershipManager(BasePermission):
    def has_permission(self, request, view):
        return can_manage_members(request.user)


class ActiveMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_active and
            hasattr(request.user, 'munc_member') and request.user.munc_member.status in {'active', 'alumni'})
