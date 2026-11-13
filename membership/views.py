import csv
import io
import uuid
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction, IntegrityError
from django.db.models import Q
from django.core import signing
from django.utils.crypto import salted_hmac, constant_time_compare
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import BaseThrottle
from accounts.throttles import quota, limit_login
from registrations.parsers import BoundedJSONParser
from registrations.storage import get_provider
from .models import StudentIdentity, MembershipRole, MUNCMember, MembershipApplication, ActivationInvitation, MembershipAuditLog, VerifiedContact
from .permissions import MembershipManager, ActiveMember, can_manage_members
from .serializers import IdentitySerializer, RoleSerializer, MemberSerializer, ProfileSerializer, ApplicationSerializer, ApplicationInput, LookupInput, PasswordInput, InvitationSerializer, AuditSerializer
from .verification import StudentVerificationService
from . import services


class MembershipThrottle(BaseThrottle):
    def allow_request(self, request, view):
        quota(self.get_ident(request), 'membership-ip', 60, 60)
        if getattr(view, 'public_action', False) and request.method == 'POST':
            quota(self.get_ident(request), 'membership-sensitive', 12, 900)
        return True


@method_decorator(csrf_protect, name='dispatch')
@method_decorator(sensitive_post_parameters('password', 'old_password', 'token'), name='dispatch')
class Base(APIView):
    permission_classes = [AllowAny]
    parser_classes = [BoundedJSONParser]
    throttle_classes = [MembershipThrottle]
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method in {'POST', 'PATCH'} and not isinstance(request.data, dict):
            raise ValidationError('Supply a JSON object.')
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'private, no-store'
        response['Referrer-Policy'] = 'no-referrer'
        return response


LOOKUP_SALT = 'membership-student-confirmation-v1'


def lookup_session(request):
    if not request.session.session_key:
        request.session.create()
    return salted_hmac(LOOKUP_SALT, request.session.session_key, algorithm='sha256').hexdigest()


class StudentLookup(Base):
    public_action = True
    def post(self, request):
        serializer = LookupInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                identity = StudentVerificationService().verify(serializer.validated_data['registration_number'])
                services.audit('application_identity_preview', identity=identity.pk)
        except IntegrityError:
            raise ValidationError('Unable to check this record. Please contact the club office.') from None
        token = signing.dumps({'identity': identity.pk, 'session': lookup_session(request)}, salt=LOOKUP_SALT)
        student_id = identity.student_id or ''
        return Response({'lookup_token': token, 'expires_in': 600, 'student': {
            'registration_number': identity.registration_number, 'full_name': identity.full_name,
            'department': identity.department,
            'student_id': ('••••' + student_id[-4:]) if student_id else ''},
            'detail': 'Is this you? Confirm this record before submitting. Confirmation does not grant account access.'})


class Apply(Base):
    public_action = True
    def post(self, request):
        serializer = ApplicationInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        number = data.pop('registration_number')
        token = data.pop('lookup_token')
        data.pop('identity_confirmed')
        data.pop('consent')
        try:
            checked = signing.loads(token, salt=LOOKUP_SALT, max_age=600)
            if not isinstance(checked, dict) or not constant_time_compare(checked.get('session', ''), lookup_session(request)):
                raise signing.BadSignature()
            identity_id = checked['identity']
        except (signing.BadSignature, KeyError, TypeError):
            raise ValidationError({'lookup_token': 'Your student check expired or is invalid. Check your record again.'}) from None
        reference = str(uuid.uuid4())
        try:
            with transaction.atomic():
                identity = get_object_or_404(StudentIdentity.objects.select_for_update(), pk=identity_id)
                if identity.registration_number.casefold() != number.strip().casefold():
                    raise ValidationError({'registration_number': 'Check this registration number again before submitting.'})
                if not MembershipApplication.objects.filter(student_identity=identity).exists() and not MUNCMember.objects.filter(student_identity=identity).exists():
                    application = MembershipApplication.objects.create(student_identity=identity, identity_confirmed_at=timezone.now(), **data)
                    reference = str(application.application_reference)
                    services.audit('application_submitted', application=str(application.pk), self_declared_member=application.is_existing_member)
                    quota(application.contact_email.casefold(), 'membership-receipt', 2, 3600)
                    services.email('membership_application_received', application.contact_email, identity.full_name, f'application:{application.pk}')
        except IntegrityError:
            pass
        return Response({'detail': 'Application request received. After review and approval, the club will email you a link to activate your account.', 'reference': reference}, status=202)


class Activate(Base):
    public_action = True
    purpose = 'activation'
    def post(self, request):
        serializer = PasswordInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.redeem(serializer.validated_data['token'], self.purpose, serializer.validated_data['password'])
        return Response({'detail': 'Account updated. You can now sign in.'})


class ResetConfirm(Activate):
    purpose = 'reset'


class MemberLogin(Base):
    public_action = True
    def post(self, request):
        identifier = request.data.get('identifier', '')
        password = request.data.get('password', '')
        if not isinstance(identifier, str) or not isinstance(password, str) or len(identifier) > 254 or len(password) > 128:
            raise ValidationError('Invalid credentials.')
        identifier = identifier.strip()
        limit_login(request, identifier)
        member = MUNCMember.objects.select_related('user').filter(student_identity__registration_number__iexact=identifier).first()
        if not member:
            contact = VerifiedContact.objects.filter(kind='email', value=identifier.casefold(), is_current=True).select_related('member__user').first()
            member = contact.member if contact else None
        if member:
            user = authenticate(request=request._request, username=member.user.username, password=password)
        else:
            make_password(password)  # Match password hashing cost for unknown identities.
            user = None
        if not user or member.status not in {'active', 'alumni'}:
            services.audit('login_failed')
            return Response({'detail': 'Invalid member credentials.'}, status=401)
        login(request._request, user)
        request.session.set_expiry(60 * 60 * 4)
        services.audit('login', user, member)
        return Response({'member': MemberSerializer(member).data, 'csrf_token': get_token(request)})


class MemberLogout(Base):
    def post(self, request):
        logout(request._request)
        return Response(status=204)


class ResetRequest(Base):
    public_action = True
    def post(self, request):
        identifier = request.data.get('identifier', '')
        if not isinstance(identifier, str) or len(identifier) > 254: raise ValidationError('Invalid request.')
        quota(identifier.strip().casefold(), 'membership-recovery', 3, 3600)
        member = MUNCMember.objects.filter(student_identity__registration_number__iexact=identifier.strip()).first()
        if not member:
            contact = VerifiedContact.objects.filter(kind='email', value=identifier.strip().casefold(), is_current=True).select_related('member').first()
            member = contact.member if contact else None
        if member and member.user.is_active and member.status in {'active', 'alumni'} and services.member_email(member):
            try:
                services.issue_invitation(member, None, 'Verified account recovery email', purpose='reset')
            except ValidationError:
                pass  # Cooldown does not reveal account existence.
        return Response({'detail': 'If an eligible account exists, recovery instructions will be sent to its verified email.'})


class Me(Base):
    permission_classes = [ActiveMember]
    def get(self, request):
        return Response(MemberSerializer(request.user.munc_member).data)
    def patch(self, request):
        serializer = ProfileSerializer(request.user.munc_member, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        services.audit('profile_updated', request.user, request.user.munc_member)
        return Response(MemberSerializer(request.user.munc_member).data)


class ChangePassword(Base):
    permission_classes = [ActiveMember]
    def post(self, request):
        old, new = request.data.get('old_password'), request.data.get('password')
        if not isinstance(old, str) or not isinstance(new, str) or len(old) > 128 or len(new) > 128: raise ValidationError('Invalid password input.')
        if not request.user.check_password(old): raise ValidationError({'old_password': 'Current password is incorrect.'})
        try: validate_password(new, request.user)
        except DjangoValidationError as exc: raise ValidationError({'password': exc.messages}) from None
        with transaction.atomic():
            member = MUNCMember.objects.select_for_update().get(user=request.user)
            request.user.set_password(new)
            request.user.save(update_fields=['password'])
            services.invalidate(member)
            services.audit('password_changed', request.user, member)
        update_session_auth_hash(request._request, request.user)
        return Response({'detail': 'Password updated. Other sessions are invalidated.'})


class ChangeEmail(Base):
    permission_classes = [ActiveMember]
    def post(self, request):
        from rest_framework import serializers
        if request.data.get('token'):
            services.redeem(str(request.data['token']), 'email', owner=request.user)
            return Response({'detail': 'Email verified and updated.'})
        address = serializers.EmailField().run_validation(request.data.get('email')).casefold()
        password = request.data.get('password', '')
        if not isinstance(password, str) or len(password) > 128 or not request.user.check_password(password): raise ValidationError('Confirm your password to change email.')
        if VerifiedContact.objects.filter(kind='email', value=address, is_current=True).exclude(member=request.user.munc_member).exists():
            raise ValidationError('This email cannot be used. Contact the club office.')
        services.issue_invitation(request.user.munc_member, request.user, 'Password-confirmed email change request', purpose='email', target_email=address)
        return Response({'detail': 'Verification queued. Your email will change only after confirmation.'})


class Photo(Base):
    permission_classes = [ActiveMember]
    parser_classes = [MultiPartParser]
    def get_member(self, request, **kwargs): return request.user.munc_member
    def get(self, request, **kwargs):
        member = self.get_member(request, **kwargs)
        if not member.photo_id: return Response({'detail': 'No profile photo.'}, status=404)
        provider = get_provider()
        if provider.name != member.photo_provider: raise ValidationError('Photo storage is temporarily unavailable.')
        try:
            with provider.open(member.photo_id) as source:
                if hasattr(source, 'iter_content'):
                    chunks, total = [], 0
                    for chunk in source.iter_content(65536):
                        total += len(chunk)
                        if total > 2*1024*1024: raise ValueError()
                        chunks.append(chunk)
                    content = b''.join(chunks)
                else: content = source.read(2*1024*1024+1)
        except Exception: raise ValidationError('Photo is temporarily unavailable.') from None
        if len(content) > 2*1024*1024: raise ValidationError('Photo exceeds size limit.')
        response = HttpResponse(content, content_type='image/png')
        response['X-Content-Type-Options'] = 'nosniff'
        return response
    def post(self, request, **kwargs):
        from PIL import Image, UnidentifiedImageError
        member = self.get_member(request, **kwargs)
        file = request.FILES.get('photo')
        if not file or file.size > 2*1024*1024 or file.content_type not in {'image/png', 'image/jpeg'}:
            raise ValidationError({'photo': 'Upload a PNG or JPEG up to 2 MiB.'})
        try:
            with Image.open(file) as image:
                if image.format not in {'PNG', 'JPEG'} or image.width * image.height > 16_000_000: raise ValueError()
                image.load()
                clean = image.convert('RGB')
                clean.thumbnail((1024, 1024))
                output = io.BytesIO()
                clean.save(output, format='PNG')
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise ValidationError({'photo': 'Invalid or unsafe image.'}) from None
        provider = get_provider()
        file_id = f'applications/{uuid.uuid4().hex}.png'
        try:
            provider.upload(file_id, SimpleUploadedFile('profile.png', output.getvalue(), content_type='image/png'))
            with transaction.atomic():
                locked = MUNCMember.objects.select_for_update().get(pk=member.pk)
                previous = (locked.photo_provider, locked.photo_id)
                locked.photo_provider, locked.photo_id = provider.name, file_id
                locked.save(update_fields=['photo_provider', 'photo_id', 'updated_at'])
                services.audit('photo_updated', request.user, locked)
        except Exception:
            try: provider.delete(file_id)
            except Exception: pass
            raise ValidationError({'photo': 'Photo could not be saved. Please retry.'}) from None
        if previous[0] == provider.name and previous[1]:
            try: provider.delete(previous[1])
            except Exception: pass
        return Response({'detail': 'Profile photo updated.'})


class AdminPhoto(Photo):
    permission_classes = [MembershipManager]
    http_method_names = ['get', 'head', 'options']
    def get_member(self, request, pk):
        member = get_object_or_404(MUNCMember, pk=pk)
        services.audit('member_photo_viewed', request.user, member)
        return member


class AdminBase(Base):
    permission_classes = [MembershipManager]


class VerifyStudent(AdminBase):
    def post(self, request):
        number = request.data.get('registration_number', '')
        if not isinstance(number, str): raise ValidationError('Invalid registration number.')
        try:
            with transaction.atomic():
                identity = StudentVerificationService().verify(number.strip())
                services.audit('student_record_checked', request.user, identity=identity.pk)
        except IntegrityError: raise ValidationError('Student verification could not be completed. Contact the club office.') from None
        return Response(IdentitySerializer(identity).data)


class MemberList(AdminBase, generics.ListAPIView):
    serializer_class = MemberSerializer
    def get_queryset(self):
        rows = MUNCMember.objects.select_related('student_identity', 'role').prefetch_related('verified_contacts')
        search = self.request.query_params.get('search', '')[:100]
        if search: rows = rows.filter(Q(student_identity__registration_number__icontains=search) | Q(student_identity__full_name__icontains=search))
        if self.request.query_params.get('status'): rows = rows.filter(status=self.request.query_params['status'])
        return rows
    def post(self, request):
        from rest_framework import serializers
        identity = get_object_or_404(StudentIdentity, pk=serializers.IntegerField(min_value=1).run_validation(request.data.get('identity')))
        role = get_object_or_404(MembershipRole, pk=serializers.IntegerField(min_value=1).run_validation(request.data.get('role')), is_active=True)
        evidence = serializers.CharField(min_length=10, max_length=1000).run_validation(request.data.get('identity_evidence'))
        address = serializers.EmailField(allow_blank=True).run_validation(request.data.get('verified_email', '')).casefold()
        try: member = services.create_member(identity, role, request.user, evidence, address)
        except IntegrityError: raise ValidationError('Identity or verified contact is already assigned.') from None
        return Response(MemberSerializer(member).data, status=201)


class MemberDetail(AdminBase):
    def get(self, request, pk):
        member = get_object_or_404(MUNCMember, pk=pk)
        services.audit('member_viewed', request.user, member)
        return Response(MemberSerializer(member).data)
    def patch(self, request, pk):
        from rest_framework import serializers
        if set(request.data) != {'role'}: raise ValidationError('Only membership role can be changed here.')
        role = get_object_or_404(MembershipRole, pk=serializers.IntegerField(min_value=1).run_validation(request.data['role']), is_active=True)
        with transaction.atomic():
            member = get_object_or_404(MUNCMember.objects.select_for_update(), pk=pk)
            member.role = role
            member.save(update_fields=['role', 'updated_at'])
            services.audit('role_changed', request.user, member, role=role.pk)
        return Response(MemberSerializer(member).data)


class MemberAction(AdminBase):
    def post(self, request, pk, action):
        from rest_framework import serializers
        with transaction.atomic():
            member = get_object_or_404(MUNCMember.objects.select_for_update(), pk=pk)
            if action == 'invite':
                evidence = serializers.CharField(min_length=10, max_length=1000).run_validation(request.data.get('identity_evidence'))
                invitation, private_url = services.issue_invitation(member, request.user, evidence, request.data.get('delivery_method', 'email'))
                data = InvitationSerializer(invitation).data
                if private_url: data['private_invitation_url'] = private_url
                return Response(data, status=201)
            if action not in {'suspend', 'reactivate', 'expire', 'alumni'}: return Response(status=404)
            evidence = serializers.CharField(min_length=10, max_length=1000).run_validation(request.data.get('reason'))
            previous = member.status
            if action == 'reactivate' and previous not in {'suspended', 'expired'}: raise ValidationError('Only suspended or expired memberships can be restored.')
            if not member.joined_at: raise ValidationError('A pending account must complete activation first.')
            member.status = {'suspend': 'suspended', 'reactivate': 'active', 'expire': 'expired', 'alumni': 'alumni'}[action]
            member.user.is_active = member.status in {'active', 'alumni'}
            member.user.save(update_fields=['is_active'])
            member.save(update_fields=['status', 'updated_at'])
            services.invalidate(member)
            # Invalidate existing sessions even if membership is later restored.
            if action in {'suspend', 'expire'}:
                from django.contrib.sessions.models import Session
                for session in Session.objects.filter(expire_date__gte=timezone.now()).iterator():
                    if session.get_decoded().get('_auth_user_id') == str(member.user_id): session.delete()
            services.audit(f'membership_{action}', request.user, member, previous=previous, reason=evidence)
            if action == 'suspend': services.email('membership_suspended', services.member_email(member), member.student_identity.full_name, f'suspended:{uuid.uuid4()}')
            return Response(MemberSerializer(member).data)


class ApplicationList(AdminBase, generics.ListAPIView):
    serializer_class = ApplicationSerializer
    def get_queryset(self):
        rows = MembershipApplication.objects.select_related('student_identity')
        if self.request.query_params.get('status'): rows = rows.filter(status=self.request.query_params['status'])
        search = self.request.query_params.get('search', '')[:100]
        if search: rows = rows.filter(Q(student_identity__registration_number__icontains=search) | Q(student_identity__full_name__icontains=search))
        return rows


class ApplicationReview(AdminBase):
    def post(self, request, pk, action):
        if action not in {'approve', 'reject', 'under_review'}: return Response(status=404)
        with transaction.atomic():
            application = get_object_or_404(MembershipApplication.objects.select_for_update(), pk=pk)
            status = {'approve': 'approved', 'reject': 'rejected', 'under_review': 'under_review'}[action]
            if application.status == 'approved' and status != 'approved': raise ValidationError('Approved applications cannot be reversed. Manage membership separately.')
            if application.status != status:
                application.status, application.reviewed_by, application.reviewed_at = status, request.user, timezone.now()
                application.save()
                services.audit('application_reviewed', request.user, application=str(application.pk), status=status)
                if status in {'approved', 'rejected'}:
                    services.email(f'membership_{status}', application.contact_email, 'Applicant', f'application:{application.pk}:{status}')
            return Response(ApplicationSerializer(application).data)


class RoleList(AdminBase, generics.ListCreateAPIView):
    serializer_class = RoleSerializer
    queryset = MembershipRole.objects.order_by('name')
    def perform_create(self, serializer):
        role = serializer.save()
        services.audit('membership_role_created', self.request.user, role=role.pk)


class RoleDetail(AdminBase, generics.UpdateAPIView):
    serializer_class = RoleSerializer
    queryset = MembershipRole.objects.all()
    http_method_names = ['patch', 'options']
    def perform_update(self, serializer):
        role = serializer.save()
        services.audit('membership_role_updated', self.request.user, role=role.pk)


class InvitationList(AdminBase, generics.ListAPIView):
    serializer_class = InvitationSerializer
    queryset = ActivationInvitation.objects.all()


class RevokeInvitation(AdminBase):
    def post(self, request, pk):
        invitation = get_object_or_404(ActivationInvitation, pk=pk)
        with transaction.atomic():
            member = MUNCMember.objects.select_for_update().get(pk=invitation.member_id)
            services.invalidate(member, invitation.purpose)
            services.audit('invitation_revoked', request.user, member, invitation=str(pk))
        return Response({'detail': 'Outstanding invitations of this type revoked.'})


class AuditList(AdminBase, generics.ListAPIView):
    serializer_class = AuditSerializer
    def get_queryset(self):
        rows = MembershipAuditLog.objects.all()
        if self.request.query_params.get('member'):
            from rest_framework import serializers
            rows = rows.filter(member_id=serializers.UUIDField().run_validation(self.request.query_params['member']))
        return rows


class Export(AdminBase):
    def get(self, request):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Membership ID', 'Name', 'Registration', 'Department', 'Role', 'Status', 'Joined'])
        for member in MUNCMember.objects.select_related('student_identity', 'role').iterator():
            row = [str(member.membership_id), member.student_identity.full_name, member.student_identity.registration_number,
                member.student_identity.department, member.role.name, member.status, str(member.joined_at or '')]
            writer.writerow(["'" + value if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')) else value for value in row])
        services.audit('members_exported', request.user)
        response = HttpResponse('\ufeff' + output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="munc-members.csv"'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class Announcements(Base):
    permission_classes = [ActiveMember]
    def get(self, request):
        # Official authored notices only; no invented activity.
        from .models import MemberAnnouncement
        return Response(list(MemberAnnouncement.objects.filter(is_published=True).order_by('-created_at').values('id', 'title', 'body', 'created_at')[:20]))
