import html
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit
from rest_framework.exceptions import ValidationError

VARIABLES = {'full_name', 'first_name', 'event_name', 'registration_id', 'registration_type', 'application_status', 'event_date', 'event_venue', 'submission_date', 'next_instructions', 'event_url', 'payment_amount', 'verified_at'}
TOKEN = re.compile(r'{{\s*([a-z_]+)\s*}}')


class EmailHTML(HTMLParser):
    allowed = {'p', 'br', 'strong', 'b', 'em', 'i', 'u', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'blockquote', 'a', 'div', 'span', 'table', 'tbody', 'tr', 'td', 'th'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.result = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.allowed:
            return
        safe = ''
        if tag == 'a':
            href = dict(attrs).get('href', '')
            parsed = urlsplit(href.strip())
            if href.strip() == '{{event_url}}' or (parsed.scheme in {'http', 'https', 'mailto'} and not parsed.username and not parsed.password and not (parsed.hostname or '').endswith('cloudinary.com')):
                safe = ' href="' + html.escape(href, quote=True) + '" rel="noopener noreferrer"'
        self.result.append('<' + tag + safe + '>')

    def handle_endtag(self, tag):
        if tag in self.allowed and tag != 'br':
            self.result.append('</' + tag + '>')

    def handle_data(self, data):
        self.result.append(html.escape(data, quote=False))


def sanitize(value):
    parser = EmailHTML()
    try:
        parser.feed(value)
        parser.close()
    except (ValueError, TypeError):
        raise ValidationError('Invalid email HTML.') from None
    return ''.join(parser.result)


def validate_content(subject, html_content, text_content):
    if not subject.strip() or '\n' in subject or '\r' in subject or len(subject) > 255:
        raise ValidationError({'subject': 'Use a nonempty single-line subject of at most 255 characters.'})
    if not text_content.strip() or len(text_content) > 100000 or len(html_content) > 150000:
        raise ValidationError({'text_content': 'Plain text is required; content exceeds the supported size or is empty.'})
    for value in (subject, html_content, text_content):
        if 'cloudinary.com' in value.casefold():
            raise ValidationError({'content': 'Private storage links must not be included in emails.'})
        if set(TOKEN.findall(value)) - VARIABLES or any(part in TOKEN.sub('', value) for part in ('{{', '}}', '{%', '%}')):
            raise ValidationError({'content': 'Only the documented personalization variables are allowed.'})
    return sanitize(html_content)


def render(subject, html_content, text_content, context):
    html_content = validate_content(subject, html_content, text_content)
    def substitute(value, escape=False):
        return TOKEN.sub(lambda match: html.escape(str(context.get(match[1], '')), quote=True) if escape else str(context.get(match[1], '')), value)
    rendered_subject = substitute(subject).replace('\r', ' ').replace('\n', ' ')[:255]
    return rendered_subject, sanitize(substitute(html_content, True)), substitute(text_content)
