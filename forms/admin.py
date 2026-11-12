from accounts.admin_scopes import EventScopedAdminMixin
import json
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.html import format_html
from rest_framework.exceptions import ValidationError as APIValidationError
from .models import FormField, FormVersion, RegistrationForm
from .services import draft_schema, duplicate_form, publish_form


@admin.register(RegistrationForm)
class RegistrationFormAdmin(EventScopedAdminMixin, admin.ModelAdmin):
    list_display = ['title', 'event', 'form_type', 'status', 'capacity', 'submission_count']
    list_filter = ['status', 'form_type']
    search_fields = ['title', 'slug', 'event__title']
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['event']
    readonly_fields = ['status', 'submission_count', 'created_at', 'updated_at', 'preview']
    actions = ['publish_selected', 'close_selected', 'archive_selected', 'duplicate_selected']

    def get_readonly_fields(self, request, obj=None):
        return list(self.readonly_fields) + (['event'] if obj else [])

    @admin.display(description='Draft preview (JSON schema)')
    def preview(self, obj):
        return format_html('<pre>{}</pre>', json.dumps(draft_schema(obj), indent=2)) if obj.pk else 'Save the form, then add fields.'

    def save_model(self, request, obj, form, change):
        if change:
            old = RegistrationForm.objects.select_for_update().get(pk=obj.pk)
            obj.submission_count = old.submission_count
            if old.event_id != obj.event_id:
                raise ValidationError('An existing form cannot be moved to another event.')
        super().save_model(request, obj, form, change)

    @admin.action(description='Publish draft schema as a new immutable version')
    def publish_selected(self, request, queryset):
        for form in queryset:
            try:
                publish_form(form.pk)
                self.message_user(request, f'Published {form.title}.')
            except (ValidationError, APIValidationError) as exc:
                self.message_user(request, f'{form.title}: {exc}', level=messages.ERROR)

    @admin.action(description='Duplicate selected forms as new drafts')
    def duplicate_selected(self, request, queryset):
        import uuid
        for form in queryset:
            clone = duplicate_form(form.pk, f'Copy of {form.title}'[:255], f'copy-{uuid.uuid4().hex}')
            self.message_user(request, f'Created draft {clone.title} ({clone.slug}).')

    @admin.action(description='Close selected forms')
    def close_selected(self, request, queryset):
        self.set_status(queryset, RegistrationForm.Status.CLOSED)

    @admin.action(description='Archive selected forms')
    def archive_selected(self, request, queryset):
        self.set_status(queryset, RegistrationForm.Status.ARCHIVED)

    @staticmethod
    @transaction.atomic
    def set_status(queryset, status):
        for form in queryset.select_for_update():
            form.status = status
            form.save(update_fields=['status', 'updated_at'])


@admin.register(FormField)
class FormFieldAdmin(EventScopedAdminMixin, admin.ModelAdmin):
    event_path = 'form__event_id'
    list_display = ['key', 'label', 'form', 'field_type', 'required', 'display_order']
    list_filter = ['field_type', 'required']
    search_fields = ['key', 'label', 'form__title']
    autocomplete_fields = ['form']

    def get_readonly_fields(self, request, obj=None):
        return ['key', 'form'] if obj else []

    def save_model(self, request, obj, form, change):
        RegistrationForm.objects.select_for_update().get(pk=obj.form_id)
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        with transaction.atomic():
            RegistrationForm.objects.select_for_update().get(pk=obj.form_id)
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            list(RegistrationForm.objects.select_for_update().filter(pk__in=queryset.values('form_id')).order_by('pk'))
            queryset.delete()


@admin.register(FormVersion)
class FormVersionAdmin(EventScopedAdminMixin, admin.ModelAdmin):
    event_path = 'form__event_id'
    read_for_reviewers = True
    list_display = ['form', 'number', 'published_at']
    readonly_fields = ['form', 'number', 'schema', 'published_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
