from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html_join
from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'version', 'submitted_by', 'created_at']
    list_filter = ['version__form']
    search_fields = ['submitted_by__username', 'version__form__title']
    readonly_fields = ['id', 'version', 'submitted_by', 'answers', 'created_at', 'uploaded_files']

    @admin.display(description='Private file answers')
    def uploaded_files(self, obj):
        return format_html_join(' ', '<a href="{}">{}</a>', [
            (reverse('forms:file-download', kwargs={'pk': item.pk}), item.field_key)
            for item in obj.files.all()])

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
