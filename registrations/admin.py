from accounts.admin_scopes import EventScopedAdminMixin
from accounts.roles import is_super_admin
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
