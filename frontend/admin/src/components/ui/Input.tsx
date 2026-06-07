import type { InputHTMLAttributes } from 'react';
import { forwardRef } from 'react';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, Props>(({ label, error, className = '', ...props }, ref) => (
  <div className="flex flex-col gap-1.5">
    {label && (
      <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{label}</label>
    )}
    <input
      ref={ref}
      className={`px-3 py-2 text-sm rounded transition-colors ${className}`}
      style={{
        background: 'var(--bg-tertiary)',
        border: `1px solid ${error ? 'var(--accent-danger)' : 'var(--border-default)'}`,
        color: 'var(--text-primary)',
      }}
      {...props}
    />
    {error && <span className="text-xs" style={{ color: 'var(--accent-danger)' }}>{error}</span>}
  </div>
));
Input.displayName = 'Input';
export default Input;
