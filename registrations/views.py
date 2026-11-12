import json
from pathlib import Path
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
from .serializers import PublicSubmissionSerializer, SubmissionSummarySerializer, SubmissionDetailSerializer, SubmissionStatusSerializer
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
        form = public_form(slug)
        serializer = PublicSubmissionSerializer(data=submission_payload(request))
        serializer.is_valid(raise_exception=True)
        throttle_email(serializer.validated_data['applicant_email'])
        submission = submit_application(form.pk, serializer.validated_data['applicant_email'],
            serializer.validated_data['version'], serializer.validated_data['answers'], request.FILES)
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
        queryset = scope_queryset(FormSubmission.objects.all(), self.request.user)
        for key in ('event', 'registration_form'):
            if key in self.request.query_params:
                value = self.request.query_params[key]
                if not value.isdecimal() or len(value) > 15:
                    raise ValidationError({key: 'Expected a numeric ID.'})
                queryset = queryset.filter(**{f'{key}_id': int(value)})
        if 'status' in self.request.query_params:
            status = self.request.query_params['status']
            if status not in FormSubmission.Status.values:
                raise ValidationError({'status': 'Unknown status.'})
            queryset = queryset.filter(status=status)
        if 'reference_number' in self.request.query_params:
            queryset = queryset.filter(reference_number=self.request.query_params['reference_number'])
        return queryset


class SubmissionDetail(PrivateStaffResponseMixin, generics.RetrieveAPIView):
    permission_classes = [ApplicationReviewPermission]
    def get_queryset(self):
        return scope_queryset(FormSubmission.objects.select_related('form_version').prefetch_related('files'), self.request.user)
    serializer_class = SubmissionDetailSerializer


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
        return response
