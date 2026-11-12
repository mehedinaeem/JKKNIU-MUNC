from django.contrib.admin.apps import AdminConfig
from django.db.models.signals import post_migrate
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    label = "accounts"

    def ready(self):
        from .roles import sync_roles_after_migrate
        post_migrate.connect(sync_roles_after_migrate, dispatch_uid='accounts.roles.setup')


class RoleAdminConfig(AdminConfig):
    default_site = 'accounts.admin_site.RoleAdminSite'
