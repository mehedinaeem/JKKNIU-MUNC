"""Example seed data only. Instances are editable database drafts, never page layouts."""
def option(value, label):
    return {'value': value, 'label': label}


def question(key, label, kind='short_text', required=False, **extra):
    return {'key': key, 'label': label, 'field_type': kind, 'required': required, **extra}


COMMITTEES = [option('general-assembly', 'General Assembly'), option('security-council', 'Security Council')]
CONSENT = question('data_processing_consent', 'Consent to data processing', 'consent', True,
    help_text='I agree to the collection and use of these details for this event’s application review. Review the organiser’s privacy information before agreeing.')
CONTACT = [question('full_name', 'Full name', required=True), question('email', 'Email', 'email', True),
           question('phone', 'Phone', 'phone', True), question('institution', 'Institution', required=True)]
TEMPLATES = {
    'delegate': {
        'title': 'Delegate Registration', 'description': 'Apply to participate as a delegate. Please review the event information before completing your application.',
        'fields': CONTACT + [
            question('department', 'Department'),
            question('academic_year', 'Academic year', 'dropdown', True, options=[option(str(year), f'Year {year}') for year in range(1, 5)] + [option('graduate', 'Graduate'), option('other', 'Other')]),
            question('previous_mun_experience', 'Previous MUN experience', 'long_text'),
            question('committee_preferences', 'Committee preferences', 'checkboxes', True, options=COMMITTEES),
            question('country_preferences', 'Country preferences', 'long_text', help_text='List your preferred countries in order of preference.'),
            question('accommodation_preference', 'Accommodation preference', 'radio', True,
                     options=[option('requested', 'I would like accommodation'), option('not-requested', 'I do not need accommodation')],
                     help_text='Availability is subject to organiser confirmation.'),
            question('passport_photo', 'Passport-size photo', 'file', True, allowed_extensions=['png', 'jpg', 'jpeg'], max_file_size=2*1024*1024),
            question('payment_transaction_id', 'Payment transaction ID', help_text='Complete only if payment is required for this event. Follow the organiser’s payment instructions.'),
            question('payment_screenshot', 'Payment screenshot', 'file', allowed_extensions=['png', 'jpg', 'jpeg', 'pdf'], max_file_size=5*1024*1024,
                     help_text='A receipt is supporting evidence only; uploading it does not verify payment.'),
            CONSENT,
        ],
    },
    'executive-board': {
        'title': 'Executive Board Application', 'description': 'Apply to serve on the Executive Board. Tell us about your experience and motivation.',
        'fields': CONTACT + [
            question('preferred_committee', 'Preferred committee', 'dropdown', True, options=COMMITTEES),
            question('preferred_position', 'Preferred position', 'dropdown', True,
                     options=[option('chair', 'Chair'), option('vice-chair', 'Vice Chair'), option('rapporteur', 'Rapporteur')]),
            question('previous_eb_experience', 'Previous EB experience', 'long_text'),
            question('mun_achievements', 'MUN achievements', 'long_text'),
            question('cv', 'CV upload', 'file', True, allowed_extensions=['pdf'], max_file_size=5*1024*1024),
            question('motivation_statement', 'Motivation statement', 'long_text', True, validation={'min_length': 100, 'max_length': 5000}),
            question('interview_availability', 'Interview availability', 'long_text', help_text='List suitable dates and times, including your timezone.'),
            CONSENT,
        ],
    },
}
