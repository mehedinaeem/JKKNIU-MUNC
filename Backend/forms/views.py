from django.db import IntegrityError
from django.urls import reverse
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from registrations.parsers import BoundedJSONParser, BoundedMultipartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from events.models import Event
from accounts.permissions import EventManagementPermission
from accounts.roles import scope_queryset
from .models import RegistrationForm
from .serializers import DraftFormSerializer, DuplicateFormSerializer, SubmissionInputSerializer
from .services import availability_error, draft_schema, duplicate_form, publish_form, submit_form


def public_form(slug):
    return get_object_or_404(RegistrationForm.objects.select_related('event').filter(
        status='published', event__status='published', versions__isnull=False).distinct(), slug=slug)


def published_data(form):
    version = form.versions.first()
    error = availability_error(form)
    return {'id': form.pk, 'slug': form.slug, 'event_slug': form.event.slug,
            'version': version.number, 'schema': version.schema,
            'accepting_submissions': error is None, 'unavailable_reason': error}


class EventFormList(generics.ListAPIView):
    permission_classes = [AllowAny]

    def list(self, request, event_slug):
        event = get_object_or_404(Event, slug=event_slug, status='published')
        forms = event.registration_forms.filter(status='published', versions__isnull=False).distinct().select_related('event')
        page = self.paginate_queryset(forms)
        return self.get_paginated_response([published_data(form) for form in page])


class PublicFormDetail(APIView):
    permission_classes = [AllowAny]

    def get(self, request, form_slug):
        return Response(published_data(public_form(form_slug)))


class StaffFormCreate(generics.CreateAPIView):
    permission_classes = [EventManagementPermission]
    serializer_class = DraftFormSerializer


class StaffFormDetail(generics.RetrieveUpdateAPIView):
    permission_classes = [EventManagementPermission]
    serializer_class = DraftFormSerializer
    def get_queryset(self):
        return scope_queryset(RegistrationForm.objects.prefetch_related('fields'), self.request.user)

    http_method_names = ['get', 'patch', 'head', 'options']


class StaffFormPreview(APIView):
    permission_classes = [EventManagementPermission]

    def get(self, request, pk):
        return Response({'draft': True, 'schema': draft_schema(get_object_or_404(scope_queryset(RegistrationForm.objects.all(), request.user), pk=pk))})


class StaffFormPublish(APIView):
    permission_classes = [EventManagementPermission]
    permission_action = 'change'

    def post(self, request, pk):
        get_object_or_404(scope_queryset(RegistrationForm.objects.all(), request.user), pk=pk)
        version = publish_form(pk)
        return Response({'id': version.form_id, 'version': version.number, 'schema': version.schema}, status=201)


class StaffFormDuplicate(APIView):
    permission_classes = [EventManagementPermission]
    permission_action = 'add'

    def post(self, request, pk):
        get_object_or_404(scope_queryset(RegistrationForm.objects.all(), request.user), pk=pk)
        serializer = DuplicateFormSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            form = duplicate_form(pk, **serializer.validated_data)
        except IntegrityError as exc:
            raise ValidationError({'slug': 'This slug is already in use.'}) from exc
        return Response(DraftFormSerializer(form).data, status=201)


class FormSubmit(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [BoundedJSONParser, BoundedMultipartParser]

    def get_throttles(self):
        from registrations.throttles import SubmissionIPThrottle
        return [SubmissionIPThrottle()]

    def post(self, request, form_slug):
        from registrations.throttles import throttle_email
        throttle_email(request.user.email.strip().casefold())
        form = public_form(form_slug)
        from registrations.views import submission_payload
        payload = submission_payload(request)
        serializer = SubmissionInputSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        submission = submit_form(form.pk, request.user, serializer.validated_data['version'],
                                 serializer.validated_data['answers'], request.FILES)
        return Response({'id': str(submission.pk), 'version': submission.version.number,
                         'created_at': submission.created_at,
                         'files': [{'field_key': item.field_key,
                                    'download_url': reverse('forms:file-download', kwargs={'pk': item.pk})}
                                   for item in submission.files.all()]}, status=201)
