import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

// Native modal dialogs provide focus trapping, background inertness and focus restoration.
export default function EventDialog({ children, labelId, onClose, className = '', onKeyDown }) {
    const ref = useRef(null);
    const timer = useRef(null);
    const [closing, setClosing] = useState(false);
    useEffect(() => {
        const dialog = ref.current;
        const previousFocus = document.activeElement;
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';
        dialog.showModal();
        return () => {
            clearTimeout(timer.current);
            dialog.close();
            document.body.style.overflow = previousOverflow;
            if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
        };
    }, []);
    function close() {
        if (closing) return;
        setClosing(true);
        timer.current = setTimeout(onClose, window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 180);
    }
    function handleKeyDown(e) {
        // Portal events bubble through React parents; only handle this dialog's controls.
        if (!ref.current.contains(e.target)) return;
        onKeyDown?.(e);
        if (e.key !== 'Tab') return;
        const controls = [...ref.current.querySelectorAll('button:not(:disabled), a[href], input, select, summary, [tabindex="0"]')]
            .filter(element => element.getClientRects().length);
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first?.focus();
        }
    }
    return createPortal(
        <dialog ref={ref} aria-labelledby={labelId} className={`event-dialog ${className} ${closing ? 'is-closing' : ''}`}
            onCancel={e => { e.preventDefault(); e.stopPropagation(); close(); }} onKeyDown={handleKeyDown}
            onClick={e => { if (e.target === e.currentTarget) close(); }}>
            <div className="event-dialog-surface">
                <button type="button" className="event-close" aria-label="Close" onClick={close} autoFocus>✕</button>
                {children}
            </div>
        </dialog>, document.body,
    );
}
