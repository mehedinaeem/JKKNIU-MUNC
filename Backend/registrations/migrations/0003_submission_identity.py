import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone
import registrations.models


def backfill(apps, schema_editor):
    Submission = apps.get_model('registrations', 'FormSubmission')
    for submission in Submission.objects.select_related('form_version__form', 'submitted_by').iterator():
        submission.reference_number = registrations.models.public_reference()
        submission.registration_form_id = submission.form_version.form_id
        submission.event_id = submission.form_version.form.event_id
        submission.applicant_email = (submission.submitted_by.email if submission.submitted_by else '').strip().casefold()
        submission.updated_at = submission.submitted_at
        submission.save(update_fields=['reference_number', 'registration_form', 'event', 'applicant_email', 'updated_at'])


class Migration(migrations.Migration):
    dependencies = [('registrations', '0002_alter_submissionfile_file')]
    operations = [
        migrations.RenameModel('Submission', 'FormSubmission'),
        migrations.RenameField('FormSubmission', 'version', 'form_version'),
        migrations.RenameField('FormSubmission', 'created_at', 'submitted_at'),
        migrations.AlterField('FormSubmission', 'submitted_by', models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT, null=True, blank=True)),
        migrations.AddField('FormSubmission', 'reference_number', models.CharField(max_length=40, null=True)),
        migrations.AddField('FormSubmission', 'event', models.ForeignKey('events.Event', on_delete=django.db.models.deletion.PROTECT, related_name='form_submissions', null=True)),
        migrations.AddField('FormSubmission', 'registration_form', models.ForeignKey('club_forms.RegistrationForm', on_delete=django.db.models.deletion.PROTECT, related_name='submissions', null=True)),
        migrations.AddField('FormSubmission', 'applicant_email', models.EmailField(max_length=254, blank=True, default=''), preserve_default=False),
        migrations.AddField('FormSubmission', 'status', models.CharField(max_length=15, choices=[('submitted', 'Submitted'), ('under_review', 'Under review'), ('shortlisted', 'Shortlisted'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('waitlisted', 'Waitlisted')], default='submitted', db_index=True)),
        migrations.AddField('FormSubmission', 'updated_at', models.DateTimeField(auto_now=True, default=timezone.now), preserve_default=False),
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.AlterField('FormSubmission', 'reference_number', models.CharField(max_length=40, unique=True, default=registrations.models.public_reference, editable=False)),
        migrations.AlterField('FormSubmission', 'event', models.ForeignKey('events.Event', on_delete=django.db.models.deletion.PROTECT, related_name='form_submissions')),
        migrations.AlterField('FormSubmission', 'registration_form', models.ForeignKey('club_forms.RegistrationForm', on_delete=django.db.models.deletion.PROTECT, related_name='submissions')),
    ]
