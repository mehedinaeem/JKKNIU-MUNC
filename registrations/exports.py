"""Bounded staff exports; text-only spreadsheet cells, no formulas or provider URLs."""
import csv
from io import BytesIO, StringIO
import json
import re
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
from django.http import HttpResponse
from rest_framework.exceptions import ValidationError
from .models import ReviewAccessLog

MAX_ROWS = 10000
MAX_CELLS = 1000000


def safe_cell(value):
    if value is None:
        return ''
    text = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, bool)) else str(value)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]', '', text)
    # Also handle whitespace before operators, tab/CR injection and full-width operators.
    if text.lstrip().startswith(('=', '+', '-', '@', '＝', '＋', '－', '＠')) or text.startswith(('\t', '\r', '\n')):
        text = "'" + text
    if len(text) > 32767:
        raise ValidationError({'export': 'An answer exceeds the spreadsheet cell limit. Narrow the selection or use the detail view.'})
    return text


def column_name(index):
    result = ''
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def xlsx_bytes(rows):
    # Minimal standards-based XLSX, using only Python's zip/XML standard library.
    # Every value is inlineStr: user data can never become a formula or hyperlink.
    content = BytesIO()
    with ZipFile(content, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        archive.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        archive.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Applications" sheetId="1" r:id="rId1"/></sheets></workbook>')
        archive.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
        with archive.open('xl/worksheets/sheet1.xml', 'w') as sheet:
            sheet.write(b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>')
            for number, row in enumerate(rows, 1):
                cells = ''.join(f'<c r="{column_name(index)}{number}" t="inlineStr"><is><t xml:space="preserve">{escape(safe_cell(value))}</t></is></c>' for index, value in enumerate(row, 1))
                sheet.write(f'<row r="{number}">{cells}</row>'.encode('utf-8'))
            sheet.write(b'</sheetData></worksheet>')
    return content.getvalue()


def export_response(request, queryset):
    kind = request.query_params.get('file_format', 'csv')
    if kind not in {'csv', 'xlsx'}:
        raise ValidationError({'file_format': 'Choose csv or xlsx.'})
    submissions = list(queryset[:MAX_ROWS + 1])
    if len(submissions) > MAX_ROWS:
        raise ValidationError({'export': f'Exports support at most {MAX_ROWS} applications. Filter by event, form or status.'})
    columns = {}
    for submission in submissions:
        for field in submission.form_version.schema.get('fields', []):
            if field['field_type'] != 'file':
                # Version included so changed labels do not reinterpret historical answers.
                identity = (submission.form_version_id, field['key'])
                columns.setdefault(identity, f'{submission.registration_form.title} v{submission.form_version.number} / {field["label"]} [{field["key"]}]')
    if len(columns) + 7 > 16384 or (len(columns) + 7) * (len(submissions) + 1) > MAX_CELLS:
        raise ValidationError({'export': 'Too many schema columns. Filter by registration form.'})
    rows = [['Reference', 'Event', 'Form', 'Version', 'Email', 'Status', 'Submitted at (UTC)', *columns.values()]]
    for submission in submissions:
        rows.append([submission.reference_number, submission.event.title, submission.registration_form.title,
            submission.form_version.number, submission.applicant_email, submission.status, submission.submitted_at.isoformat(),
            *[submission.answers.get(key, '') if version_id == submission.form_version_id else '' for version_id, key in columns]])
    rows = [[safe_cell(value) for value in row] for row in rows]
    if sum(len(value.encode('utf-8')) for row in rows for value in row) > 20 * 1024 * 1024:
        raise ValidationError({'export': 'Export exceeds 20 MiB of text. Narrow the selection.'})
    if kind == 'csv':
        output = StringIO(newline='')
        writer = csv.writer(output)
        writer.writerows(rows)
        payload, content_type = '\ufeff' + output.getvalue(), 'text/csv; charset=utf-8'
    else:
        payload, content_type = xlsx_bytes(rows), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ReviewAccessLog.objects.create(actor=request.user, action=f'export_{kind}', metadata={
        'rows': len(submissions), 'filters': {key: request.query_params[key] for key in ('event', 'registration_form', 'status', 'ordering') if key in request.query_params}})
    response = HttpResponse(payload, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="munc-applications.{kind}"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
