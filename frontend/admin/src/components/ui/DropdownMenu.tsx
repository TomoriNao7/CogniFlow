import { useState, useRef, useEffect } from 'react';
import type { ReactNode } from 'react';

interface Item {
  label: string;
  icon?: ReactNode;
  danger?: boolean;
  onClick: () => void;
}

interface Props {
  trigger: ReactNode;
  items: Item[];
  align?: 'left' | 'right';
}

export default function DropdownMenu({ trigger, items, align = 'left' }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={ref} className="relative inline-block">
      <button onClick={() => setOpen(!open)} className="flex items-center">
        {trigger}
      </button>
      {open && (
        <div
          className="absolute z-40 mt-1.5 py-1 rounded shadow-dropdown min-w-[160px]"
          style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-default)',
            [align === 'right' ? 'right' : 'left']: 0,
          }}
        >
          {items.map((item, i) => (
            <button
              key={i}
              onClick={() => { item.onClick(); setOpen(false); }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors hover:bg-[var(--bg-tertiary)]"
              style={{ color: item.danger ? 'var(--accent-danger)' : 'var(--text-primary)' }}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
