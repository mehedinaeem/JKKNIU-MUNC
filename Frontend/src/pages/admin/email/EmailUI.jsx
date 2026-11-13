import { useEffect, useRef, useState } from 'react';
import { Button, Dialog } from '../../../components/admin/AdminUI';

export function EmailPreview({ data, onClose }) {
    return <Dialog title="Email preview" wide onClose={onClose}><h3 className="mb-4 break-words text-lg text-primary-900">{data.subject}</h3><iframe title="Sanitized email preview" sandbox="" className="h-80 w-full rounded-xl border border-slate-200 bg-white" srcDoc={`<!doctype html><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="font-family:Arial,sans-serif;padding:16px;line-height:1.7">${data.html_content}</body>`} /><details className="mt-5"><summary className="cursor-pointer text-sm font-semibold text-primary-700">Plain-text fallback</summary><pre className="mt-3 whitespace-pre-wrap break-words text-sm">{data.text_content}</pre></details>{data.recipient_count != null && <p className="mt-4 text-sm">{data.recipient_count} eligible recipients</p>}</Dialog>;
}

export function RichEmailEditor({ value, onChange, disabled = false }) {
    const ref = useRef(null);
    const [initial] = useState(value);
    useEffect(() => { ref.current.innerHTML = initial || ''; }, [initial]);
    function format(command) {
        ref.current.focus();
        document.execCommand(command, false);
        onChange(ref.current.innerHTML);
    }
    return <div><p id="email-rich-label" className="admin-label">Formatted email</p><div role="toolbar" aria-label="Email formatting" className="flex flex-wrap gap-2 rounded-t-xl border border-slate-300 bg-slate-50 p-2">{[['bold', 'Bold'], ['italic', 'Italic'], ['insertUnorderedList', 'Bullet list'], ['insertOrderedList', 'Numbered list']].map(([command, label]) => <Button key={command} variant="secondary" disabled={disabled} onClick={() => format(command)}>{label}</Button>)}</div><div ref={ref} role="textbox" aria-multiline="true" aria-labelledby="email-rich-label" contentEditable={!disabled} suppressContentEditableWarning className="min-h-48 overflow-auto whitespace-pre-wrap break-words rounded-b-xl border border-t-0 border-slate-300 bg-white p-4 text-sm leading-7 focus:outline focus:outline-2 focus:outline-primary-500" onInput={event => onChange(event.currentTarget.innerHTML)} onDrop={event => { event.preventDefault(); document.execCommand('insertText', false, event.dataTransfer.getData('text/plain')); onChange(ref.current.innerHTML); }} onPaste={event => { event.preventDefault(); document.execCommand('insertText', false, event.clipboardData.getData('text/plain')); onChange(ref.current.innerHTML); }} /><p className="admin-hint">HTML is sanitized by Django. Personalize with approved variables such as {'{{full_name}}'} and {'{{event_name}}'}.</p></div>;
}

