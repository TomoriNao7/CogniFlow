import { useEffect, useState } from 'react';
import { CheckCircle, AlertTriangle, XCircle, X } from 'lucide-react';

type ToastType = 'success' | 'warning' | 'error';

interface ToastItem { id: number; type: ToastType; message: string; }

let addToastFn: ((type: ToastType, message: string) => void) | null = null;

export function showToast(type: ToastType, message: string) {
  addToastFn?.(type, message);
}

const ICONS: Record<ToastType, typeof CheckCircle> = {
  success: CheckCircle, warning: AlertTriangle, error: XCircle,
};
const COLORS: Record<ToastType, string> = {
  success: 'var(--accent-success)', warning: 'var(--accent-warning)', error: 'var(--accent-danger)',
};

export default function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    addToastFn = (type, message) => {
      const id = Date.now();
      setToasts((t) => [...t, { id, type, message }]);
      setTimeout(() => setToasts((t) => t.filter((i) => i.id !== id)), 3500);
    };
    return () => { addToastFn = null; };
  }, []);

  return (
    <div className="fixed top-5 right-5 z-[100] flex flex-col gap-2">
      {toasts.map((t) => {
        const Icon = ICONS[t.type];
        return (
          <div key={t.id} className="toast-enter flex items-center gap-2 px-4 py-3 rounded shadow-dropdown"
               style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-default)', minWidth: '280px' }}>
            <Icon size={16} color={COLORS[t.type]} />
            <span className="text-sm flex-1" style={{ color: 'var(--text-primary)' }}>{t.message}</span>
            <button onClick={() => setToasts((t2) => t2.filter((i) => i.id !== t.id))}>
              <X size={14} style={{ color: 'var(--text-secondary)' }} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
