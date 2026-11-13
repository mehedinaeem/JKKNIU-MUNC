"""Identity approval and single-use capabilities; no provider request runs in HTTP."""
import hashlib
import secrets
import uuid
from datetime import timedelta
from urllib.parse import urlencode
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from mailing.models import EmailMessage, EmailTemplate
from mailing.rendering import render, VARIABLES
from .crypto import SECURITY_TYPES, seal
from .models import MUNCMember, ActivationInvitation, VerifiedContact, MembershipAuditLog

EMAIL_DEFAULTS = {
    'membership_application_received': ('Membership application received', 'Your application was received. It does not grant membership or account access.'),
    'membership_approved': ('Membership application approved', 'Your application is approved. An officer must independently confirm your identity before issuing a private activation invitation.'),
    'membership_rejected': ('Membership application update', 'Your membership application was not approved. Contact the club office with any questions.'),
    'membership_invitation': ('Activate your MUNC member account', 'Use your private single-use invitation to set your password: {{event_url}}'),
    'membership_activated': ('Your MUNC account is active', 'Your member account has been activated. You can now sign in to the membership portal.'),
    'membership_password_reset': ('Reset your MUNC password', 'Use this private single-use password-reset link: {{event_url}}'),
    'membership_email_verification': ('Verify your MUNC email address', 'Confirm your new email address using this single-use link: {{event_url}}'),
    'membership_suspended': ('MUNC membership suspended', 'Your membership access has been suspended. Please contact the club office.'),
}


def audit(action, actor=None, member=None, **details):
    MembershipAuditLog.objects.create(action=action, actor=actor if actor and actor.is_authenticated else None, member=member, details=details)


def email(kind, address, name, key, url=''):
    if not address: return None
    subject, text = EMAIL_DEFAULTS[kind]
    template = EmailTemplate.objects.filter(event__isnull=True, template_key=kind).first()
    context = dict.fromkeys(VARIABLES, '') | {'full_name': name, 'first_name': name.split()[0] if name else 'Member',
        'event_name': 'JKKNIU MUNC Membership', 'event_url': url, 'next_instructions': ''}
    rendered = render(template.subject if template else subject,
        template.html_content if template else '<p>Hello {{full_name}},</p><p>' + text + '</p>',
        template.text_content if template else 'Hello {{full_name}},\n' + text, context)
    html, text = rendered[1], rendered[2]
    if kind in SECURITY_TYPES:
        html, text = seal(html), seal(text)
    job, _ = EmailMessage.objects.get_or_create(event_key=f'membership:{key}', defaults={
        'event': None, 'recipient_email': address.strip().casefold(), 'message_type': kind,
        'subject': rendered[0], 'html_content': html, 'text_content': text,
        'status': 'skipped' if template and not template.is_active else 'pending'})
    return job


def member_email(member):
    contact = member.verified_contacts.filter(kind='email', is_current=True).first()
    return contact.value if contact else ''


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def invalidate(member, purpose=None):
    rows = member.invitations.filter(used_at__isnull=True, revoked_at__isnull=True)
    if purpose: rows = rows.filter(purpose=purpose)
    ids = list(rows.values_list('pk', flat=True))
    rows.update(revoked_at=timezone.now())
    EmailMessage.objects.filter(event_key__in=[f'membership:invitation:{pk}' for pk in ids], status__in=['pending', 'retry']).update(
        status='cancelled', html_content='', text_content='', last_error='Invitation invalidated.')


@transaction.atomic
def create_member(identity, role, actor, evidence, email_address=''):
    # Lock identity to serialize independent officers claiming the same student.
    identity = type(identity).objects.select_for_update().get(pk=identity.pk)
    if not settings.DEBUG and identity.verification_source == 'development_mock':
        raise ValidationError('Development fixtures cannot create production members.')
    if hasattr(identity, 'muncmember'):
        raise ValidationError('This identity already has a member profile.')
    if not evidence.strip() or len(evidence) > 1000:
        raise ValidationError({'identity_evidence': 'Record independent identity confirmation (maximum 1000 characters).'})
    if not role.is_active: raise ValidationError({'role': 'Select an active membership role.'})
    user = get_user_model().objects.create_user(username=f'member_{uuid.uuid4().hex}', first_name=identity.full_name[:150], is_active=False)
    user.set_unusable_password()
    user.save(update_fields=['password'])
    member = MUNCMember.objects.create(user=user, student_identity=identity, role=role)
    if email_address:
        VerifiedContact.objects.create(member=member, kind='email', value=email_address.strip().casefold(),
            evidence=evidence, verified_by=actor)
        user.email = email_address.strip().casefold()
        user.save(update_fields=['email'])
    audit('member_created', actor, member, independent_confirmation=evidence)
    return member


@transaction.atomic
def issue_invitation(member, actor, evidence, delivery='email', purpose='activation', target_email=''):
    member = MUNCMember.objects.select_for_update().select_related('user', 'student_identity').get(pk=member.pk)
    if purpose == 'activation' and (member.status != 'pending_activation' or member.user.is_active):
        raise ValidationError('Only pending members can receive activation invitations.')
    if purpose != 'activation' and (member.status not in {'active', 'alumni'} or not member.user.is_active):
        raise ValidationError('This member account is unavailable.')
    if delivery not in {'email', 'in_person'} or not evidence.strip() or len(evidence) > 1000:
        raise ValidationError('Independent identity confirmation and a valid delivery method are required.')
    recent = member.invitations.filter(purpose=purpose, created_at__gte=timezone.now()-timedelta(seconds=60)).exists()
    if recent: raise ValidationError('Wait at least one minute before replacing an invitation.')
    address = target_email if purpose == 'email' else member_email(member)
    if delivery == 'email' and not address:
        raise ValidationError('An independently verified email is required. Use in-person delivery instead.')
    invalidate(member, purpose)
    raw = secrets.token_urlsafe(32)
    duration = settings.MEMBERSHIP_INVITATION_HOURS if purpose == 'activation' else 1
    invitation = ActivationInvitation.objects.create(member=member, purpose=purpose, token_hash=token_hash(raw),
        expires_at=timezone.now()+timedelta(hours=duration), delivery_method=delivery,
        target_email=address, identity_evidence=evidence, created_by=actor)
    route = {'activation': '/join/activate', 'reset': '/member/reset-password', 'email': '/member/settings'}[purpose]
    # Fragment prevents private capabilities entering proxy/request/referrer logs.
    url = settings.PUBLIC_SITE_URL + route + '#' + urlencode({'token': raw})
    if delivery == 'email':
        key = {'activation': 'membership_invitation', 'reset': 'membership_password_reset', 'email': 'membership_email_verification'}[purpose]
        email(key, address, member.student_identity.full_name, f'invitation:{invitation.pk}', url)
    audit('invitation_created', actor, member, invitation=str(invitation.pk), purpose=purpose, method=delivery)
    return invitation, url if delivery == 'in_person' else None


@transaction.atomic
def redeem(raw, purpose, password='', owner=None):
    # Lock member first, then invitation, consistent with issue/revoke/suspend.
    lookup = ActivationInvitation.objects.filter(token_hash=token_hash(raw), purpose=purpose).values('member_id').first()
    if not lookup: raise ValidationError('Invitation is invalid or expired.')
    member = MUNCMember.objects.select_for_update().select_related('user', 'student_identity').get(pk=lookup['member_id'])
    invitation = ActivationInvitation.objects.select_for_update().get(token_hash=token_hash(raw), purpose=purpose)
    now = timezone.now()
    if invitation.used_at or invitation.revoked_at or invitation.expires_at <= now:
        raise ValidationError('Invitation is invalid or expired.')
    if purpose == 'activation':
        if member.status != 'pending_activation' or member.user.is_active: raise ValidationError('Invitation is invalid or expired.')
    elif member.status not in {'active', 'alumni'} or not member.user.is_active:
        raise ValidationError('Invitation is invalid or expired.')
    if purpose == 'email':
        if not owner or member.user_id != owner.pk: raise ValidationError('Invitation is invalid or expired.')
        if VerifiedContact.objects.filter(kind='email', value=invitation.target_email, is_current=True).exclude(member=member).exists():
            raise ValidationError('This email cannot be used. Contact the club office.')
        member.verified_contacts.filter(kind='email', is_current=True).update(is_current=False)
        VerifiedContact.objects.create(member=member, kind='email', value=invitation.target_email,
            evidence='Single-use email verification by authenticated account owner', verified_by=owner)
        member.user.email = invitation.target_email
        member.user.save(update_fields=['email'])
    else:
        try: validate_password(password, member.user)
        except DjangoValidationError as exc: raise ValidationError({'password': exc.messages}) from None
        member.user.set_password(password)
        member.user.is_active = True
        member.user.save(update_fields=['password', 'is_active'])
        if purpose == 'activation':
            member.status, member.joined_at = 'active', now
            member.save(update_fields=['status', 'joined_at', 'updated_at'])
            email('membership_activated', member_email(member), member.student_identity.full_name, f'activated:{member.pk}')
    invitation.used_at = now
    invitation.save(update_fields=['used_at'])
    invalidate(member)  # All outstanding capabilities become invalid after any credential change.
    audit('invitation_redeemed', owner, member, invitation=str(invitation.pk), purpose=purpose)
    return member
