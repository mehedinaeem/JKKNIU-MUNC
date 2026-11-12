import { Dialog } from '../admin/AdminUI';
import { FIELD_TYPES } from './schema';

export default function FieldPalette({ onAdd, onClose }) {
    return <Dialog title="Add a question" description="Choose the kind of answer you need." onClose={onClose} wide><div className="grid gap-3 sm:grid-cols-2">{FIELD_TYPES.map(([type, name, icon, description]) => <button key={type} type="button" className="flex min-w-0 items-start gap-3 rounded-xl border border-slate-200 p-4 text-left transition hover:border-primary-400 hover:bg-primary-50" onClick={() => onAdd(type)}><span aria-hidden="true" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-50 text-sm font-bold text-primary-700">{icon}</span><span><span className="block text-sm font-semibold text-primary-900">{name}</span><span className="mt-1 block text-xs leading-5 text-slate-500">{description}</span></span></button>)}</div></Dialog>;
}
