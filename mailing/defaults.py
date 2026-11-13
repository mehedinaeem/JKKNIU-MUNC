KEYS = ['registration_confirmation', 'application_submitted', 'application_under_review', 'application_shortlisted', 'application_approved', 'application_rejected', 'application_waitlisted', 'payment_verified', 'interview_invitation', 'conference_reminder', 'custom_announcement']
DEFAULTS = {}
for key in KEYS:
    if key == 'registration_confirmation':
        subject = 'Registration Received — {{event_name}}'
        body = 'Your {{registration_type}} application has been received. Receipt does not confirm selection or payment verification.'
    elif key == 'payment_verified':
        subject = 'Payment Verified — {{event_name}}'
        body = 'An authorized administrator verified your payment. Amount: {{payment_amount}}. Verification date: {{verified_at}}. This does not change your application selection status.'
    elif key == 'interview_invitation':
        subject = 'Interview Invitation — {{event_name}}'
        body = 'You are invited to an Executive Board interview. Please follow the interview arrangements below.'
    elif key == 'conference_reminder':
        subject = 'Event Reminder — {{event_name}}'
        body = 'This is a reminder about {{event_name}} on {{event_date}} at {{event_venue}}.'
    elif key.startswith('application_'):
        subject = 'Application Update — {{event_name}}'
        body = 'Your application status is now {{application_status}}. This notification does not verify payment.'
    else:
        subject = 'Event Update — {{event_name}}'
        body = 'Please review this event announcement.'
    text = 'Hello {{full_name}},\n\n' + body + '\n\nRegistration: {{registration_id}}\nCategory: {{registration_type}}\nSubmitted: {{submission_date}}\nStatus: {{application_status}}\n\n{{next_instructions}}\n\nOfficial event information: {{event_url}}'
    html = '<p>Hello {{full_name}},</p><p>' + body + '</p><p>Registration: {{registration_id}}<br>Category: {{registration_type}}<br>Submitted: {{submission_date}}<br>Status: {{application_status}}</p><p>{{next_instructions}}</p><p><a href="{{event_url}}">Official event information</a></p>'
    DEFAULTS[key] = {'name': key.replace('_', ' ').title(), 'template_key': key, 'subject': subject, 'html_content': html, 'text_content': text}
