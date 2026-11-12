"""Shared, scoped query construction for review lists, metrics and exports."""
import json
from django.db.models import Q, TextField
from django.db.models.functions import Cast
from rest_framework.exceptions import ValidationError
from accounts.roles import scope_queryset
from .models import FormSubmission


def review_queryset(request):
    queryset = scope_queryset(FormSubmission.objects.select_related('event', 'registration_form', 'form_version'), request.user)
    for key in ('event', 'registration_form'):
        value = request.query_params.get(key)
        if value:
            if not value.isdecimal() or len(value) > 15:
                raise ValidationError({key: 'Expected a numeric ID.'})
            queryset = queryset.filter(**{f'{key}_id': int(value)})
    status = request.query_params.get('status')
    if status:
        if status not in FormSubmission.Status.values:
            raise ValidationError({'status': 'Unknown status.'})
        queryset = queryset.filter(status=status)
    reference = request.query_params.get('reference_number')
    if reference:
        queryset = queryset.filter(reference_number=reference)
    search = request.query_params.get('search', '').strip()
    if len(search) > 200:
        raise ValidationError({'search': 'Use at most 200 characters.'})
    if search:
        # Includes custom name fields without requiring particular keys or labels.
        # SQLite stores JSON Unicode as escapes; PostgreSQL renders literal text. Match both.
        queryset = queryset.annotate(answer_text=Cast('answers', TextField())).filter(
            Q(reference_number__icontains=search) | Q(applicant_email__icontains=search)
            | Q(answer_text__icontains=search)
            | Q(answer_text__icontains=json.dumps(search, ensure_ascii=True)[1:-1]))
    order = request.query_params.get('ordering', '-submitted_at')
    if order not in ('submitted_at', '-submitted_at', 'reference_number', '-reference_number', 'status', '-status'):
        raise ValidationError({'ordering': 'Unsupported ordering.'})
    return queryset.order_by(order, 'id')
