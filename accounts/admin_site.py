from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.http import JsonResponse
from rest_framework.exceptions import APIException
from .roles import can_access_administration
from .throttles import limit_login


class RoleAdminAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not can_access_administration(user):
            raise self.get_invalid_login_error()


class RoleAdminSite(AdminSite):
    login_form = RoleAdminAuthenticationForm
    def has_permission(self, request):
        return can_access_administration(request.user)

    def login(self, request, extra_context=None):
        if request.method == 'POST':
            try:
                limit_login(request, request.POST.get('username', ''))
            except APIException as exc:
                response = JsonResponse({'detail': str(exc.detail)}, status=exc.status_code)
                if getattr(exc, 'wait', None):
                    response['Retry-After'] = str(exc.wait)
                return response
        return super().login(request, extra_context)
