type Variant = 'default' | 'success' | 'warning' | 'danger' | 'accent';

interface Props {
  children: string;
  variant?: Variant;
}

const COLORS: Record<Variant, { bg: string; text: string }> = {
  default: { bg: 'var(--bg-tertiary)', text: 'var(--text-secondary)' },
  success: { bg: 'rgba(78,205,196,0.12)',  text: 'var(--accent-success)' },
  warning: { bg: 'rgba(240,160,80,0.12)',  text: 'var(--accent-warning)' },
  danger:  { bg: 'rgba(224,85,106,0.12)',  text: 'var(--accent-danger)' },
  accent:  { bg: 'rgba(0,212,228,0.12)',   text: 'var(--accent-primary)' },
};

export default function Badge({ children, variant = 'default' }: Props) {
  const c = COLORS[variant];
  return (
    <span
      className="inline-block px-2 py-0.5 text-[11px] font-medium"
      style={{
        background: c.bg,
        color: c.text,
        clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
      }}
    >
      {children}
    </span>
  );
}
