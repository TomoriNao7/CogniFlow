import type { SelectHTMLAttributes } from 'react';
import { forwardRef } from 'react';
import { ChevronDown } from 'lucide-react';

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: Array<{ value: string; label: string }>;
}

const Select = forwardRef<HTMLSelectElement, Props>(({ label, options, className = '', ...props }, ref) => (
  <div className="flex flex-col gap-1.5">
    {label && (
      <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{label}</label>
    )}
    <div className="relative">
      <select
        ref={ref}
        className={`w-full px-3 py-2 text-sm rounded appearance-none cursor-pointer transition-colors ${className}`}
        style={{
          background: 'var(--bg-tertiary)',
          border: '1px solid var(--border-default)',
          color: 'var(--text-primary)',
        }}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none"
                   style={{ color: 'var(--text-secondary)' }} />
    </div>
  </div>
));
Select.displayName = 'Select';
export default Select;
