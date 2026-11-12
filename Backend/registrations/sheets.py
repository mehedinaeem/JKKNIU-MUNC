"""Stable question columns across immutable published versions of one form."""
def sheet_columns(form):
    columns = {}
    for version in form.versions.order_by('number').iterator():
        for field in version.schema.get('fields', []):
            columns[field['key']] = {name: field[name] for name in ('key', 'label', 'field_type')}
    return list(columns.values())
