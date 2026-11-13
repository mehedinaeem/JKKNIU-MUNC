from django.db import migrations


def seed(apps, schema_editor):
    Role = apps.get_model('membership', 'MembershipRole')
    for name in ['General Member', 'Executive Member', 'Executive Board Member', 'Committee Member', 'Club President', 'Club Secretary', 'Alumni Member']:
        Role.objects.get_or_create(name=name)
    Template = apps.get_model('mailing', 'EmailTemplate')
    templates = {
        'membership_application_received': ('Membership application received', 'Your application was received. This does not grant membership or account access.'),
        'membership_approved': ('Membership application approved', 'Your application is approved. An officer must independently confirm your identity before issuing a private invitation.'),
        'membership_rejected': ('Membership application update', 'Your membership application was not approved. Please contact the club office with questions.'),
        'membership_invitation': ('Activate your MUNC member account', 'Use your private single-use invitation to set your password: {{event_url}}'),
        'membership_activated': ('Your MUNC account is active', 'Your account is active. Sign in through the official member portal.'),
        'membership_password_reset': ('Reset your MUNC password', 'Use your private single-use password reset link: {{event_url}}'),
        'membership_email_verification': ('Verify your MUNC email address', 'Verify your new email using this private single-use link: {{event_url}}'),
        'membership_suspended': ('MUNC membership suspended', 'Your membership access is suspended. Please contact the club office.'),
    }
    for key, (subject, body) in templates.items():
        Template.objects.get_or_create(event=None, template_key=key, defaults={'name': subject, 'subject': subject,
            'html_content': '<p>Hello {{full_name}},</p><p>' + body + '</p>', 'text_content': 'Hello {{full_name}},\n' + body})


class Migration(migrations.Migration):
    dependencies = [('membership', '0001_initial'), ('mailing', '0005_alter_emailmessage_event')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
