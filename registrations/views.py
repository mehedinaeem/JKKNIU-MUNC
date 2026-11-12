import json
from pathlib import Path
from django.db.models import Q
from forms.models import RegistrationForm
from django.http import FileResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import ValidationError, PermissionDenied
from registrations.parsers import BoundedJSONParser, BoundedMultipartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import ApplicationReviewPermission
from accounts.roles import scope_queryset, can_review_event
from forms.views import public_form
from .models import FormSubmission, SubmissionFile
from .serializers import PublicSubmissionSerializer, SubmissionSummarySerializer, SubmissionDetailSerializer, SubmissionStatusSerializer, ReviewedSubmissionSerializer
from .services import submit_application, change_status
from .storage import get_provider
from .throttles import SubmissionIPThrottle, throttle_email, SubmissionUnavailable


def submission_payload(request):
    if request.content_type.startswith('multipart/'):
        # Access request.data first so Django/DRF parses the multipart stream once.
        request.data
        try:
            payload = json.loads(request.POST.get('payload', ''))
        except (ValueError, TypeError):
            raise ValidationError({'payload': 'Expected a JSON submission object.'}) from None
        if any(len(request.FILES.getlist(key)) != 1 for key in request.FILES):
            raise ValidationError({'files': 'Only one file per question is supported.'})
        return payload
    return request.data


class PublicFormSubmit(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    parser_classes = [BoundedJSONParser, BoundedMultipartParser]
    throttle_classes = [SubmissionIPThrottle]

    def post(self, request, slug):
        serializer = PublicSubmissionSerializer(data=submission_payload(request))
        serializer.is_valid(raise_exception=True)
        throttle_email(serializer.validated_data['applicant_email'])
        key = serializer.validated_data.get('submission_key')
        visible = Q(status='published', event__status='published', versions__isnull=False)
        if key:
            visible |= Q(submissions__submission_key=key)
        form = get_object_or_404(RegistrationForm.objects.filter(visible).distinct(), slug=slug)
        submission = submit_application(form.pk, serializer.validated_data['applicant_email'],
            serializer.validated_data['version'], serializer.validated_data['answers'], request.FILES, submission_key=key)
        return Response({'reference_number': submission.reference_number,
                         'message': 'Your application has been received.'}, status=201,
                        headers={'Cache-Control': 'no-store'})


class PrivateStaffResponseMixin:
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'private, no-store'
        return response


class SubmissionList(PrivateStaffResponseMixin, generics.ListAPIView):
    permission_classes = [ApplicationReviewPermission]
    serializer_class = SubmissionSummarySerializer

    def get_queryset(self):
        from .review import review_queryset
        return review_queryset(self.request)


class SubmissionDetail(PrivateStaffResponseMixin, generics.RetrieveAPIView):
    permission_classes = [ApplicationReviewPermission]
    def get_queryset(self):
        return scope_queryset(FormSubmission.objects.select_related('form_version', 'event', 'registration_form').prefetch_related('files', 'reviewer_notes__author', 'status_changes__changed_by'), self.request.user)
    serializer_class = ReviewedSubmissionSerializer


class SubmissionStatus(PrivateStaffResponseMixin, APIView):
    permission_classes = [ApplicationReviewPermission]

    def patch(self, request, pk):
        get_object_or_404(scope_queryset(FormSubmission.objects.all(), request.user), pk=pk)
        serializer = SubmissionStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submission = change_status(pk, serializer.validated_data['status'], request.user)
        return Response(SubmissionSummarySerializer(submission).data)


class PrivateFileDownload(PrivateStaffResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        item = get_object_or_404(SubmissionFile.objects.select_related('submission'), pk=pk)
        # Anonymous applicants have no file retrieval endpoint. A reference is not an access token.
        if item.submission.submitted_by_id != request.user.pk and not can_review_event(request.user, item.submission.event_id):
            raise PermissionDenied()
        try:
            if item.storage_provider == 'legacy_local':
                source = item.file.open('rb')
            else:
                source = get_provider(item.storage_provider).open(item.provider_file_id)
        except Exception:
            raise SubmissionUnavailable() from None
        if item.storage_provider == 'cloudinary':
            def chunks():
                try:
                    yield from source.iter_content(chunk_size=64 * 1024)
                finally:
                    source.close()
            response = StreamingHttpResponse(chunks(), content_type='application/octet-stream')
            response._resource_closers.append(source.close)
        else:
            response = FileResponse(source, content_type='application/octet-stream')
        # Generated filename avoids exposing applicant names in download headers.
        from django.utils.http import content_disposition_header
        suffix = Path(item.original_filename or item.file.name).suffix.lower()
        response['Content-Disposition'] = content_disposition_header(True, 'attachment' + suffix)
        response['X-Content-Type-Options'] = 'nosniff'
        from .models import ReviewAccessLog
        ReviewAccessLog.objects.create(actor=request.user, action='file_download', submission=item.submission, metadata={'file_id': item.pk})
        return response


class SubmissionNotes(PrivateStaffResponseMixin, APIView):
    permission_classes = [ApplicationReviewPermission]

    def post(self, request, pk):
        from .serializers import ReviewerNoteSerializer
        submission = get_object_or_404(scope_queryset(FormSubmission.objects.all(), request.user), pk=pk)
        serializer = ReviewerNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = serializer.save(submission=submission, author=request.user)
        return Response(ReviewerNoteSerializer(note).data, status=201)


class ReviewDashboard(PrivateStaffResponseMixin, APIView):
    permission_classes = [ApplicationReviewPermission]

    def get(self, request):
        from django.db.models import Count
        from events.models import Event
        submissions = scope_queryset(FormSubmission.objects.all(), request.user)
        counts = dict(submissions.values('status').annotate(total=Count('pk')).values_list('status', 'total'))
        return Response({'total_events': scope_queryset(Event.objects.all(), request.user, 'pk').count(),
            'published_forms': scope_queryset(RegistrationForm.objects.filter(status='published'), request.user).count(),
            'total_submissions': sum(counts.values()),
            'statuses': {status: counts.get(status, 0) for status in FormSubmission.Status.values}})


from rest_framework.throttling import UserRateThrottle


class ReviewExportThrottle(UserRateThrottle):
    scope = 'review_exports'
    rate = '10/min'


class SubmissionExport(PrivateStaffResponseMixin, APIView):
    permission_classes = [ApplicationReviewPermission]
    throttle_classes = [ReviewExportThrottle]

    def get(self, request):
        from .exports import export_response
        from .review import review_queryset
        return export_response(request, review_queryset(request))


class ReviewFormList(PrivateStaffResponseMixin, generics.ListAPIView):
    permission_classes = [ApplicationReviewPermission]

    def get_serializer_class(self):
        from forms.serializers import FormSummarySerializer
        return FormSummarySerializer

    def get_queryset(self):
        from django.db.models import Count
        return scope_queryset(RegistrationForm.objects.select_related('event').prefetch_related('versions').annotate(field_count=Count('fields')), self.request.user)


class FormSubmissionSheet(PrivateStaffResponseMixin, generics.GenericAPIView):
    permission_classes = [ApplicationReviewPermission]

    def get(self, request, pk):
        from .review import review_queryset
        from .sheets import sheet_columns
        from .serializers import SheetSubmissionSerializer
        form = get_object_or_404(scope_queryset(RegistrationForm.objects.select_related('event'), request.user), pk=pk)
        rows = review_queryset(request).filter(registration_form=form).prefetch_related('files')
        page = self.paginate_queryset(rows)
        response = self.get_paginated_response(SheetSubmissionSerializer(page, many=True).data)
        response.data.update({'form': {'id': form.pk, 'title': form.title, 'slug': form.slug,
            'event': form.event_id, 'event_title': form.event.title, 'status': form.status},
            'columns': sheet_columns(form), 'page_number': self.paginator.page.number,
            'page_size': self.paginator.page.paginator.per_page,
            'total_pages': self.paginator.page.paginator.num_pages})
        return response


class PrivateImagePreview(PrivateStaffResponseMixin, APIView):
    permission_classes = [ApplicationReviewPermission]

    def get(self, request, pk):
        from django.http import HttpResponse
        from .images import image_preview
        from .models import ReviewAccessLog
        item = get_object_or_404(SubmissionFile.objects.select_related('submission'), pk=pk)
        if not can_review_event(request.user, item.submission.event_id):
            raise PermissionDenied()
        if item.content_type not in {'image/png', 'image/jpeg'} or item.storage_provider == 'legacy_local':
            raise ValidationError({'file': 'An image preview is not available. Use the authorized file download.'})
        size = request.query_params.get('size', 'thumbnail')
        if size not in {'thumbnail', 'large'}:
            raise ValidationError({'size': 'Choose thumbnail or large.'})
        try:
            source = get_provider(item.storage_provider).open(item.provider_file_id)
            data = image_preview(source, item.storage_provider, item.content_type, size == 'large')
        except Exception:
            raise SubmissionUnavailable() from None
        ReviewAccessLog.objects.create(actor=request.user, action='file_preview', submission=item.submission,
            metadata={'file_id': item.pk, 'size': size})
        response = HttpResponse(data, content_type=item.content_type)
        response['Content-Disposition'] = 'inline; filename="private-image.png"' if item.content_type == 'image/png' else 'inline; filename="private-image.jpg"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response
