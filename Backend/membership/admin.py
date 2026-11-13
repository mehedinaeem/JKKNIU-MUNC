from django.contrib import admin
from .models import StudentIdentity, MembershipRole, MembershipApplication, MUNCMember, ActivationInvitation, VerifiedContact, MembershipAuditLog, MemberAnnouncement
from .permissions import can_manage_members


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_module_permission(self, request): return can_manage_members(request.user)
    def has_view_permission(self, request, obj=None): return can_manage_members(request.user)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


for model in [StudentIdentity, MembershipApplication, MUNCMember, VerifiedContact, MembershipAuditLog]:
    admin.site.register(model, ReadOnlyAdmin)


@admin.register(ActivationInvitation)
class InvitationAdmin(ReadOnlyAdmin):
    exclude = ['token_hash', 'target_email', 'identity_evidence']
    list_display = ['id', 'member', 'purpose', 'expires_at', 'used_at', 'revoked_at']


@admin.register(MembershipRole)
class RoleAdmin(admin.ModelAdmin):
    def has_module_permission(self, request): return can_manage_members(request.user)
    def has_view_permission(self, request, obj=None): return can_manage_members(request.user)
    def has_add_permission(self, request): return can_manage_members(request.user)
    def has_change_permission(self, request, obj=None): return can_manage_members(request.user)
    def has_delete_permission(self, request, obj=None): return False


@admin.register(MemberAnnouncement)
class AnnouncementAdmin(RoleAdmin):
    list_display = ['title', 'is_published', 'created_at']
    readonly_fields = ['created_by', 'created_at']
    def save_model(self, request, obj, form, change):
        if not change: obj.created_by = request.user
        super().save_model(request, obj, form, change)
