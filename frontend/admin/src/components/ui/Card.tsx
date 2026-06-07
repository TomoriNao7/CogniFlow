import type { ReactNode } from 'react';

interface Props {
  children: ReactNode;
  className?: string;
  accent?: boolean;  /* 一级卡片：顶部强调色条 */
  onClick?: () => void;
}

export default function Card({ children, className = '', accent, onClick }: Props) {
  return (
    <div
      className={`card ${onClick ? 'cursor-pointer' : ''} ${className}`}
      style={{ padding: '20px' }}
      onClick={onClick}
    >
      {accent && (
        <div className="-mx-5 -mt-5 mb-4 h-0.5" style={{ background: 'var(--accent-primary)' }} />
      )}
      {children}
    </div>
  );
}
