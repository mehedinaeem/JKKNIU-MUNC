"""Bounded, declarative schema and answer validation. No expressions or regex execution."""
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import validate_email, URLValidator
from rest_framework.exceptions import ValidationError

TYPES = {'short_text', 'long_text', 'email', 'phone', 'integer', 'decimal', 'date',
         'dropdown', 'radio', 'checkboxes', 'file', 'url', 'consent'}
SELECTION = {'dropdown', 'radio', 'checkboxes'}
SAFE_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_UPLOAD = 10 * 1024 * 1024
MAX_FIELDS = 100


def invalid(message):
    raise ValidationError(message)


def numeric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        invalid('Expected a number.')
    if len(str(value)) > 100:
        invalid('Number is too long.')
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        invalid('Expected a number.')
    if not number.is_finite() or abs(number) > Decimal('999999999999999999'):
        invalid('Number must be finite and within supported bounds.')
    return number


def validate_answer(field, value):
    kind = field['field_type']
    rules = field.get('validation', {})
    if kind == 'file':
        if not isinstance(value, UploadedFile):
            invalid('An uploaded file is required; file paths and URLs are not accepted.')
        extension = Path(value.name).suffix.lower().lstrip('.')
        if extension not in field['allowed_extensions'] or extension not in SAFE_EXTENSIONS:
            invalid('File extension is not allowed.')
        if not 0 < value.size <= field['max_file_size']:
            invalid('File is empty or exceeds the size limit.')
        from registrations.file_validation import validate_upload
        return validate_upload(value, field)
    if kind in {'short_text', 'long_text', 'email', 'phone', 'url'}:
        if not isinstance(value, str):
            invalid('Expected text.')
        limit = 100000 if kind == 'long_text' else (10000 if kind == 'short_text' else 1000)
        if len(value) > min(limit, rules.get('max_length', limit)) or len(value) < rules.get('min_length', 0):
            invalid('Text length is outside allowed bounds.')
        if field.get('required') and not value.strip():
            invalid('This field is required.')
        try:
            if kind == 'email':
                validate_email(value)
            elif kind == 'url':
                URLValidator(schemes=['https', 'http'])(value)
            elif kind == 'phone' and (not re.fullmatch(r'\+?[0-9 ()-]{7,30}', value)
                                      or not 7 <= sum(char.isdigit() for char in value) <= 15):
                invalid('Enter a phone number with 7–30 digits/separator characters.')
        except DjangoValidationError:
            invalid(f'Invalid {kind}.')
        return value
    if kind in {'integer', 'decimal'}:
        number = numeric(value)
        if kind == 'integer' and number != number.to_integral_value():
            invalid('Expected a whole number.')
        if kind == 'decimal' and number.as_tuple().exponent < -6:
            invalid('At most six decimal places are supported.')
        if 'min_value' in rules and number < numeric(rules['min_value']):
            invalid('Number is below the minimum.')
        if 'max_value' in rules and number > numeric(rules['max_value']):
            invalid('Number exceeds the maximum.')
        return int(number) if kind == 'integer' else format(number, 'f')
    if kind == 'date':
        if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
            invalid('Expected an ISO date (YYYY-MM-DD).')
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            invalid('Invalid date.')
        if 'min_date' in rules and parsed < date.fromisoformat(rules['min_date']):
            invalid('Date is before the minimum.')
        if 'max_date' in rules and parsed > date.fromisoformat(rules['max_date']):
            invalid('Date exceeds the maximum.')
        return parsed.isoformat()
    if kind in SELECTION:
        allowed = {option['value'] for option in field['options']}
        if kind == 'checkboxes':
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                invalid('Expected a list of choice values.')
            if len(value) != len(set(value)) or any(item not in allowed for item in value):
                invalid('Invalid or repeated choice.')
            if len(value) < rules.get('min_choices', 0) or len(value) > rules.get('max_choices', len(allowed)):
                invalid('Number of choices is outside allowed bounds.')
            if field.get('required') and not value:
                invalid('This field is required.')
        elif not isinstance(value, str) or value not in allowed:
            invalid('Invalid choice.')
        return value
    if kind == 'consent':
        if type(value) is not bool:
            invalid('Expected a boolean.')
        if field.get('required') and value is not True:
            invalid('Consent is required.')
        return value
    invalid('Unsupported field type.')


def validate_field_definition(field):
    kind = field['field_type']
    if kind not in TYPES:
        invalid('Unsupported field type.')
    rules = field.get('validation', {})
    if not isinstance(rules, dict):
        invalid('validation must be an object.')
    permitted = ({'min_length', 'max_length'} if kind in {'short_text', 'long_text', 'email', 'phone', 'url'}
                 else {'min_value', 'max_value'} if kind in {'integer', 'decimal'}
                 else {'min_date', 'max_date'} if kind == 'date'
                 else {'min_choices', 'max_choices'} if kind == 'checkboxes' else set())
    if set(rules) - permitted:
        invalid('Unsupported validation rules for this field type.')
    for key, value in rules.items():
        if key in {'min_length', 'max_length', 'min_choices', 'max_choices'}:
            if type(value) is not int or not 0 <= value <= 100000:
                invalid('Length and choice bounds must be nonnegative bounded integers.')
        elif key in {'min_value', 'max_value'}:
            numeric(value)
        else:
            try:
                if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
                    raise ValueError
                date.fromisoformat(value)
            except ValueError:
                invalid('Date bounds must use YYYY-MM-DD.')
    for lo, hi in [('min_length', 'max_length'), ('min_value', 'max_value'),
                   ('min_date', 'max_date'), ('min_choices', 'max_choices')]:
        if lo in rules and hi in rules:
            first, last = (numeric(rules[lo]), numeric(rules[hi])) if lo == 'min_value' else (rules[lo], rules[hi])
            if first > last:
                invalid('Minimum cannot exceed maximum.')
    if kind in {'short_text', 'long_text', 'email', 'phone', 'url'}:
        limit = 100000 if kind == 'long_text' else (10000 if kind == 'short_text' else 1000)
        if any(rules.get(key, 0) > limit for key in ('min_length', 'max_length')):
            invalid('Text validation bounds exceed the supported field limit.')
    options = field.get('options', [])
    if not isinstance(options, list) or len(options) > 200:
        invalid('Options must be a list of at most 200 choices.')
    values = []
    for option in options:
        if not isinstance(option, dict) or set(option) != {'value', 'label'}:
            invalid('Each option needs only value and label.')
        if any(not isinstance(option[key], str) or not option[key].strip() or len(option[key]) > 255 for key in ('value', 'label')):
            invalid('Choice values and labels must be nonempty text of at most 255 characters.')
        values.append(option['value'])
    if len(values) != len(set(values)):
        invalid('Choice values must be unique.')
    if kind == 'checkboxes' and any(rules.get(key, 0) > len(options) for key in ('min_choices', 'max_choices')):
        invalid('Choice count bounds exceed the available options.')
    if kind in SELECTION and not options:
        invalid('Selection fields require options.')
    if kind not in SELECTION and options:
        invalid('Options are supported only for selection fields.')
    extensions = field.get('allowed_extensions', [])
    if not isinstance(extensions, list) or any(not isinstance(x, str) or x not in SAFE_EXTENSIONS for x in extensions):
        invalid('Unsupported file extensions.')
    size = field.get('max_file_size')
    if kind == 'file':
        if not extensions or type(size) is not int or not 1 <= size <= MAX_UPLOAD:
            invalid('File fields require allowed_extensions and a maximum size of 1–10485760 bytes.')
    elif extensions or size is not None:
        invalid('File constraints are only supported for file fields.')
    default = field.get('default_value')
    if default is not None:
        if kind == 'file' or kind == 'consent':
            invalid('File and consent fields cannot have defaults.')
        validate_answer({**field, 'required': False}, default)
    return field


def validate_answers(schema, answers, files=None):
    if not isinstance(answers, dict):
        invalid({'answers': 'Expected an object keyed by stable field keys.'})
    files = files or {}
    fields = {field['key']: field for field in schema['fields']}
    errors, clean, uploads = {}, {}, {}
    for unknown in (set(answers) | set(files)) - set(fields):
        errors[unknown] = 'Unknown field.'
    for key, field in fields.items():
        if key in answers and key in files:
            errors[key] = 'Supply an answer or a file, not both.'
            continue
        value = files.get(key) if key in files else answers.get(key)
        if value is None or value == '' or (value == [] and field['field_type'] == 'checkboxes'):
            if field['required']:
                errors[key] = 'This field is required.'
            continue
        try:
            value = validate_answer(field, value)
            if field['field_type'] == 'file':
                uploads[key] = value
            else:
                clean[key] = value
        except ValidationError as exc:
            errors[key] = exc.detail
    if errors:
        invalid({'answers': errors})
    return clean, uploads
