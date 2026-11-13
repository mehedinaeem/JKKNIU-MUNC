import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class StudentIdentity(models.Model):
    registration_number = models.CharField(max_length=64, unique=True)
    student_id = models.CharField(max_length=64, null=True, blank=True, unique=True)
    full_name = models.CharField(max_length=255)
    department = models.CharField(max_length=255)
    session = models.CharField(max_length=100, blank=True)
    verification_source = models.CharField(max_length=100)
    verified_at = models.DateTimeField(default=timezone.now)
    last_checked_at = models.DateTimeField(default=timezone.now)


class MembershipRole(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)


class MembershipApplication(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted'
        UNDER_REVIEW = 'under_review'
        APPROVED = 'approved'
        REJECTED = 'rejected'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_identity = models.OneToOneField(StudentIdentity, on_delete=models.PROTECT)
    application_reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    motivation = models.TextField(blank=True)
    is_existing_member = models.BooleanField(null=True, blank=True)
    identity_confirmed_at = models.DateTimeField(null=True, blank=True)
    experience = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_preference = models.CharField(max_length=20, default='email')
    consent_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']


class MUNCMember(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending_activation'
        ACTIVE = 'active'
        SUSPENDED = 'suspended'
        EXPIRED = 'expired'
        ALUMNI = 'alumni'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='munc_member')
    student_identity = models.OneToOneField(StudentIdentity, on_delete=models.PROTECT)
    role = models.ForeignKey(MembershipRole, on_delete=models.PROTECT)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING, db_index=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    biography = models.TextField(blank=True)
    contact_preference = models.CharField(max_length=20, default='email')
    photo_provider = models.CharField(max_length=20, blank=True)
    photo_id = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        permissions = [('manage_membership', 'Manage club membership and independently confirm identity')]


class VerifiedContact(models.Model):
    member = models.ForeignKey(MUNCMember, on_delete=models.PROTECT, related_name='verified_contacts')
    kind = models.CharField(max_length=10, choices=[('email', 'Email'), ('phone', 'Phone')])
    value = models.CharField(max_length=254)
    evidence = models.CharField(max_length=1000)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    verified_at = models.DateTimeField(default=timezone.now)
    is_current = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['kind', 'value'], condition=Q(is_current=True), name='membership_unique_current_contact')]


class ActivationInvitation(models.Model):
    class Purpose(models.TextChoices):
        ACTIVATION = 'activation'
        RESET = 'reset'
        EMAIL = 'email'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.ForeignKey(MUNCMember, on_delete=models.PROTECT, related_name='invitations')
    purpose = models.CharField(max_length=12, choices=Purpose.choices, default=Purpose.ACTIVATION)
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    delivery_method = models.CharField(max_length=12, choices=[('email', 'Verified email'), ('in_person', 'In person')])
    target_email = models.EmailField(blank=True)
    identity_evidence = models.CharField(max_length=1000)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class MembershipAuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    member = models.ForeignKey(MUNCMember, null=True, on_delete=models.PROTECT)
    action = models.CharField(max_length=60)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class MemberAnnouncement(models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_published = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
