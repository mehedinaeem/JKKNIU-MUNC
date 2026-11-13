from rest_framework import serializers
from .roles import ROLE_NAMES, is_super_admin


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=1024, write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if set(self.initial_data) != {'username', 'password'}:
            raise serializers.ValidationError('Only username and password are accepted.')
        return attrs


def administrator_data(user):
    roles = set(user.groups.filter(name__in=ROLE_NAMES).values_list('name', flat=True))
    if is_super_admin(user):
        roles.add('Super Admin')
    if user.has_perm('membership.manage_membership') and not is_super_admin(user):
        roles.add('Membership Admin')
    return {'id': user.pk, 'username': user.get_username(), 'roles': sorted(roles),
            'all_events': is_super_admin(user),
            'can_manage_members': is_super_admin(user) or user.has_perm('membership.manage_membership'),
            'assigned_event_ids': list(user.event_assignments.values_list('event_id', flat=True))}
