from django.contrib import admin
from accounts.roles import is_super_admin
from .models import EmailTemplate, EmailCampaign, EmailMessage, EmailDeliveryAttempt, EmailPreference, PaymentVerification, PaymentChange, EventEmailSettings, EmailWebhookEvent


class EmailAuditAdmin(admin.ModelAdmin):
    def has_module_permission(self, request): return is_super_admin(request.user)
    def has_view_permission(self, request, obj=None): return is_super_admin(request.user)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
    def get_readonly_fields(self, request, obj=None): return [field.name for field in self.model._meta.fields]


for model in (EmailTemplate, EmailCampaign, EmailMessage, EmailDeliveryAttempt, EmailPreference, PaymentVerification, PaymentChange, EventEmailSettings, EmailWebhookEvent):
    admin.site.register(model, EmailAuditAdmin)
