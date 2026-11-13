from rest_framework import serializers
from .models import StudentIdentity, MembershipRole, MUNCMember, MembershipApplication, ActivationInvitation, MembershipAuditLog


class IdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentIdentity
        fields = ['id', 'registration_number', 'student_id', 'full_name', 'department', 'session', 'verification_source', 'verified_at', 'last_checked_at']
        read_only_fields = fields


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipRole
        fields = ['id', 'name', 'description', 'is_active']


class MemberSerializer(serializers.ModelSerializer):
    identity = IdentitySerializer(source='student_identity', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    verified_contacts = serializers.SerializerMethodField()
    class Meta:
        model = MUNCMember
        fields = ['id', 'membership_id', 'identity', 'role', 'role_name', 'status', 'joined_at', 'biography', 'contact_preference', 'verified_contacts', 'updated_at']
        read_only_fields = fields
    def get_verified_contacts(self, obj):
        return list(obj.verified_contacts.filter(is_current=True).values('kind', 'value', 'verified_at'))


class ProfileSerializer(serializers.ModelSerializer):
    contact_preference = serializers.ChoiceField(choices=['email', 'phone', 'none'])
    class Meta:
        model = MUNCMember
        fields = ['biography', 'contact_preference']
        extra_kwargs = {'biography': {'max_length': 3000}}
    def to_internal_value(self, data):
        if set(data) - set(self.fields):
            raise serializers.ValidationError({'non_field_errors': ['Verified identity and membership fields are read-only.']})
        return super().to_internal_value(data)


class ApplicationSerializer(serializers.ModelSerializer):
    identity = IdentitySerializer(source='student_identity', read_only=True)
    class Meta:
        model = MembershipApplication
        fields = ['id', 'identity', 'application_reference', 'motivation', 'is_existing_member', 'identity_confirmed_at', 'experience', 'contact_email', 'contact_preference', 'status', 'created_at', 'reviewed_at']
        read_only_fields = fields


class LookupInput(serializers.Serializer):
    registration_number = serializers.RegexField(r'^[A-Za-z0-9/-]{3,64}$', max_length=64)
    consent = serializers.BooleanField()
    def validate_consent(self, value):
        if not value: raise serializers.ValidationError('Consent is required to check your student record.')
        return value


class ApplicationInput(serializers.Serializer):
    registration_number = serializers.RegexField(r'^[A-Za-z0-9/-]{3,64}$', max_length=64)
    lookup_token = serializers.CharField(max_length=1000)
    identity_confirmed = serializers.BooleanField()
    is_existing_member = serializers.BooleanField()
    motivation = serializers.CharField(max_length=5000, required=False, allow_blank=True, default='')
    experience = serializers.CharField(max_length=5000, required=False, allow_blank=True, default='')
    contact_email = serializers.EmailField()
    contact_preference = serializers.ChoiceField(choices=['email', 'phone', 'none'], default='email')
    consent = serializers.BooleanField()
    def validate_consent(self, value):
        if not value: raise serializers.ValidationError('Consent is required to process your application.')
        return value

    def validate(self, attrs):
        if not attrs['identity_confirmed']:
            raise serializers.ValidationError({'identity_confirmed': 'Confirm that this is your student record.'})
        if not attrs['is_existing_member'] and len(attrs.get('motivation', '').strip()) < 20:
            raise serializers.ValidationError({'motivation': 'Tell us why you would like to join (at least 20 characters).'})
        if attrs['is_existing_member']:
            attrs['motivation'] = ''
            attrs['experience'] = ''
        return attrs


class PasswordInput(serializers.Serializer):
    token = serializers.CharField(min_length=40, max_length=128, trim_whitespace=False)
    password = serializers.CharField(min_length=8, max_length=128, trim_whitespace=False)


class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivationInvitation
        fields = ['id', 'member', 'purpose', 'expires_at', 'used_at', 'revoked_at', 'delivery_method', 'created_at']
        read_only_fields = fields


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipAuditLog
        fields = ['id', 'actor', 'member', 'action', 'details', 'created_at']
        read_only_fields = fields
