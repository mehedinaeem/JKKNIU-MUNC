from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [('registrations', '0003_submission_identity')]
    operations = [migrations.AddField('SubmissionFile', 'created_at', models.DateTimeField(auto_now_add=True, default=timezone.now), preserve_default=False)]
