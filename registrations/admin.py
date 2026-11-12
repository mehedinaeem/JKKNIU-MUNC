from accounts.admin_scopes import EventScopedAdminMixin
from .services import change_status
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html_join
from .models import FormSubmission


@admin.register(FormSubmission)
class SubmissionAdmin(EventScopedAdminMixin, admin.ModelAdmin):
    review_model = True
    list_display = ['reference_number', 'registration_form', 'status', 'submitted_at']
    list_filter = ['status']
    search_fields = ['reference_number']
    readonly_fields = ['id', 'reference_number', 'event', 'registration_form', 'form_version',
                       'submitted_by', 'applicant_email', 'answers', 'status', 'submitted_at',
                       'updated_at', 'uploaded_files']

    @admin.display(description='Private file answers')
    def uploaded_files(self, obj):
        return format_html_join(' ', '<a href="{}">{}</a>', [
            (reverse('forms:file-download', kwargs={'pk': item.pk}), item.field_key)
            for item in obj.files.all()])

    def has_add_permission(self, request):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [name for name in self.readonly_fields if name != 'status']

    def save_model(self, request, obj, form, change):
        if not self.has_change_permission(request, obj):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied()
        change_status(obj.pk, obj.status, request.user)

    def has_delete_permission(self, request, obj=None):
        return False


class ReviewNoteInline(admin.TabularInline):
    from .models import ReviewerNote
    model = ReviewerNote
    fields = ['author', 'body', 'created_at']
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_view_permission(self, request, obj=None):
        from accounts.roles import can_review_event, is_administrator
        return can_review_event(request.user, obj.event_id) if obj else is_administrator(request.user)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ReviewHistoryInline(ReviewNoteInline):
    from .models import SubmissionStatusChange
    model = SubmissionStatusChange
    fields = ['changed_by', 'previous_status', 'status', 'created_at']
    readonly_fields = fields


SubmissionAdmin.inlines = [ReviewNoteInline, ReviewHistoryInline]


from .models import ReviewAccessLog


@admin.register(ReviewAccessLog)
class ReviewAccessLogAdmin(admin.ModelAdmin):
    list_display = ['actor', 'action', 'submission', 'created_at']
    list_filter = ['action']
    readonly_fields = ['actor', 'action', 'submission', 'metadata', 'created_at']

    def has_module_permission(self, request):
        from accounts.roles import is_super_admin
        return is_super_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
