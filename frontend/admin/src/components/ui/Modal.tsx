import type { ReactNode } from 'react';
import { X } from 'lucide-react';

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: string;
}

export default function Modal({ open, onClose, title, children, width = '520px' }: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center"
         style={{ background: 'rgba(0,0,0,0.6)' }}
         onClick={onClose}>
      <div
        className="card"
        style={{ width, maxWidth: '90vw', maxHeight: '85vh', overflow: 'auto' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-[var(--bg-tertiary)] transition-colors">
            <X size={18} style={{ color: 'var(--text-secondary)' }} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
