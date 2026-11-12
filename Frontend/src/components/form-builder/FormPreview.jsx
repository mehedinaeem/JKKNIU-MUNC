import { useState } from 'react';
import { Button, Dialog } from '../admin/AdminUI';

function PreviewQuestion({ field, index, error }) {
    const id = `preview-${field.key}`;
    const helpId = `${id}-help`;
    const common = { id, name: field.key, 'aria-describedby': field.help_text ? helpId : undefined,
        required: field.required, placeholder: field.placeholder, className: 'admin-input' };
    const rules = field.validation || {};
    let control;
    if (['radio', 'checkboxes'].includes(field.field_type)) {
        control = <div className="space-y-3">{field.options.map(option => <label key={option.value} className="flex items-center gap-3 rounded-xl border border-slate-200 p-3 text-sm"><input type={field.field_type === 'radio' ? 'radio' : 'checkbox'} name={field.key} value={option.value} required={field.field_type === 'radio' && field.required} defaultChecked={Array.isArray(field.default_value) ? field.default_value.includes(option.value) : field.default_value === option.value} />{option.label || 'Untitled option'}</label>)}</div>;
    } else if (field.field_type === 'dropdown') {
        control = <select {...common} defaultValue={field.default_value || ''}><option value="">{field.placeholder || 'Select an option'}</option>{field.options.map(option => <option key={option.value} value={option.value}>{option.label || 'Untitled option'}</option>)}</select>;
    } else if (field.field_type === 'consent') {
        control = <label className="flex items-start gap-3 text-sm"><input id={id} type="checkbox" name={field.key} required={field.required} className="mt-1" />I agree</label>;
    } else if (field.field_type === 'long_text') {
        control = <textarea {...common} rows={4} minLength={rules.min_length || undefined} maxLength={rules.max_length || undefined} defaultValue={field.default_value ?? ''} />;
    } else {
        const type = { email: 'email', phone: 'tel', integer: 'number', decimal: 'number', date: 'date', file: 'file', url: 'url' }[field.field_type] || 'text';
        control = <input {...common} type={type} defaultValue={type === 'file' ? undefined : field.default_value ?? ''} step={field.field_type === 'decimal' ? 'any' : type === 'number' ? '1' : undefined} min={type === 'date' ? rules.min_date : rules.min_value} max={type === 'date' ? rules.max_date : rules.max_value} minLength={rules.min_length || undefined} maxLength={rules.max_length || undefined} accept={type === 'file' ? field.allowed_extensions.map(extension => `.${extension}`).join(',') : undefined} />;
    }
    const multi = ['radio', 'checkboxes'].includes(field.field_type);
    return <fieldset className="space-y-3"><legend className="mb-2 text-sm font-semibold text-primary-900">{index + 1}. {multi ? field.label || 'Untitled question' : <label htmlFor={id}>{field.label || 'Untitled question'}</label>}{field.required && <span className="ml-1 text-red-600" aria-label="required">*</span>}</legend>{field.help_text && <p id={helpId} className="text-xs leading-5 text-slate-500">{field.help_text}</p>}{control}{field.field_type === 'file' && <p className="admin-hint">Maximum {field.max_file_size / 1048576} MiB. Files are not uploaded in preview.</p>}{error && <p className="admin-field-error" role="alert">{error}</p>}</fieldset>;
}
export default function FormPreview({ form, onClose }) {
    const [message, setMessage] = useState('');
    const [errors, setErrors] = useState({});
    function check(event) {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const missing = {};
        form.fields.forEach(field => {
            if (field.field_type === 'checkboxes') {
                const count = data.getAll(field.key).length;
                if ((count > 0 || field.required) && (count < (field.required ? Math.max(1, field.validation.min_choices || 0) : field.validation.min_choices || 0)
                    || count > (field.validation.max_choices ?? field.options.length))) missing[field.key] = 'Check the number of selected options.';
            }
        });
        setErrors(missing);
        setMessage(Object.keys(missing).length ? 'Please check the highlighted questions.' : 'Preview checks passed. Nothing has been submitted.');
    }
    return <Dialog title="Form preview" description="Preview only. Responses are not collected here." onClose={onClose} wide><div className="mb-7 border-b border-slate-100 pb-6"><div className="mb-5 h-1.5 w-14 rounded-full bg-accent-400" /><h3 className="break-words text-2xl text-primary-900">{form.title || 'Untitled form'}</h3><p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-500">{form.description}</p></div><form onSubmit={check} className="space-y-7">{form.fields.length ? form.fields.map((field, index) => <PreviewQuestion key={field.key} field={field} index={index} error={errors[field.key]} />) : <p className="text-sm text-slate-500">Add questions to see them here.</p>}<p role="status" className="text-sm text-primary-700">{message}</p><div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-5"><Button variant="secondary" onClick={onClose}>Back to builder</Button><Button type="submit">Check required answers</Button></div></form></Dialog>;
}
