"""Django groups and model permissions determine capability; assignments determine scope."""
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps

SUPER_ADMIN = 'Super Admin'
EVENT_ADMIN = 'Event Admin'
REVIEWER = 'Reviewer'
ROLE_NAMES = (SUPER_ADMIN, EVENT_ADMIN, REVIEWER)
MANAGER_PERMISSIONS = {
    'events': {'event': ['view', 'change', 'delete']},
    'club_forms': {'registrationform': ['view', 'add', 'change', 'delete'],
                   'formfield': ['view', 'add', 'change', 'delete'], 'formversion': ['view']},
    'registrations': {'formsubmission': ['view', 'change']},
}
REVIEWER_PERMISSIONS = {
    'events': {'event': ['view']},
    'club_forms': {'registrationform': ['view'], 'formversion': ['view']},
    'registrations': {'formsubmission': ['view', 'change']},
}


def setup_roles():
    """Idempotent: reset managed role permissions without assigning any users."""
    # Explicit creation also works before post_migrate has populated later apps' permissions.
    for role, spec in ((EVENT_ADMIN, MANAGER_PERMISSIONS), (REVIEWER, REVIEWER_PERMISSIONS)):
        group, _ = Group.objects.get_or_create(name=role)
        permissions = []
        for app_label, models in spec.items():
            for model, actions in models.items():
                content_type, _ = ContentType.objects.get_or_create(app_label=app_label, model=model)
                for action in actions:
                    permission, _ = Permission.objects.get_or_create(content_type=content_type,
                        codename=f'{action}_{model}', defaults={'name': f'Can {action} {model}'})
                    permissions.append(permission)
        group.permissions.set(permissions)
    group, _ = Group.objects.get_or_create(name=SUPER_ADMIN)
    group.permissions.set(Permission.objects.all())


def sync_roles_after_migrate(sender, **kwargs):
    # Run after the last configured app's standard permission creation, including test DB setup.
    if sender.label == list(apps.get_app_configs())[-1].label:
        setup_roles()


def active_staff(user):
    return bool(user and user.is_authenticated and user.is_active and user.is_staff)


def has_role(user, *names):
    return active_staff(user) and user.groups.filter(name__in=names).exists()


def is_super_admin(user):
    return active_staff(user) and (user.is_superuser or has_role(user, SUPER_ADMIN))


def is_administrator(user):
    return is_super_admin(user) or has_role(user, EVENT_ADMIN, REVIEWER)


def can_access_administration(user):
    return is_administrator(user) or bool(active_staff(user) and user.has_perm('membership.manage_membership'))


def is_event_manager(user):
    return is_super_admin(user) or has_role(user, EVENT_ADMIN)


def can_manage_event(user, event_id, permission='events.change_event'):
    return is_super_admin(user) or bool(is_event_manager(user) and user.has_perm(permission)
        and user.event_assignments.filter(event_id=event_id).exists())


def can_review_event(user, event_id, permission='registrations.view_formsubmission'):
    return is_super_admin(user) or bool(has_role(user, EVENT_ADMIN, REVIEWER) and user.has_perm(permission)
        and user.event_assignments.filter(event_id=event_id).exists())


def scope_queryset(queryset, user, event_path='event_id'):
    if is_super_admin(user):
        return queryset
    if not is_administrator(user):
        return queryset.none()
    return queryset.filter(**{f'{event_path}__in': user.event_assignments.values('event_id')})
