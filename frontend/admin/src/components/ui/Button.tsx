import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: 'sm' | 'md';
  children: ReactNode;
}

const BASE = 'inline-flex items-center justify-center gap-1.5 font-semibold transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed';
const SIZES = { sm: 'px-3 py-1.5 text-xs', md: 'px-6 py-2 text-sm' };

const styles: Record<Variant, string> = {
  primary:  'bg-[var(--accent-primary)] text-[#0A0E14] hover:bg-[var(--accent-deep)] hover:shadow-[var(--glow-accent)]',
  secondary:'bg-transparent text-[var(--accent-primary)] border border-[var(--border-accent)] hover:bg-[rgba(0,212,228,0.08)]',
  danger:   'bg-transparent text-[var(--accent-danger)] border border-[rgba(224,85,106,0.3)] hover:bg-[rgba(224,85,106,0.1)] hover:border-[var(--accent-danger)]',
  ghost:    'bg-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]',
};

export default function Button({ variant = 'primary', size = 'md', className = '', children, ...props }: Props) {
  return (
    <button
      className={`${BASE} ${SIZES[size]} ${styles[variant]} ${className}`}
      style={{
        clipPath: variant !== 'ghost'
          ? 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)'
          : 'none',
      }}
      {...props}
    >
      {children}
    </button>
  );
}
