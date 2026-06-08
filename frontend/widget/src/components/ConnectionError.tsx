import { WifiOff, RefreshCw } from 'lucide-react';

export default function ConnectionError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
      <div
        className="w-14 h-14 flex items-center justify-center mb-3"
        style={{
          background: 'var(--bg-tertiary)',
          clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
          border: '1px solid var(--accent-danger)',
        }}
      >
        <WifiOff size={24} style={{ color: 'var(--accent-danger)' }} />
      </div>
      <p
        className="text-sm font-bold tracking-wider mb-1"
        style={{ color: 'var(--accent-danger)', fontFamily: "'JetBrains Mono', monospace" }}
      >
        [ CONNECTION LOST ]
      </p>
      <p className="text-xs mb-5" style={{ color: 'var(--text-secondary)' }}>
        服务器连接中断，请检查网络后重试
      </p>
      <button
        onClick={onRetry}
        className="flex items-center gap-2 px-5 py-2 text-sm font-bold tracking-wider transition-all duration-150"
        style={{
          background: 'var(--accent-primary)',
          color: '#1A1A28',
          borderRadius: 'var(--radius-sm)',
          fontFamily: "'JetBrains Mono', monospace",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.boxShadow = 'var(--glow-accent)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        <RefreshCw size={14} /> 重新连接
      </button>
    </div>
  );
}
