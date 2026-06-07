import { WifiOff, RefreshCw } from 'lucide-react';

interface Props {
  onRetry: () => void;
}

export default function ConnectionError({ onRetry }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
      <WifiOff size={36} style={{ color: 'var(--text-disabled)' }} />
      <p className="mt-3 text-sm" style={{ color: 'var(--text-secondary)' }}>连接已断开</p>
      <p className="mt-1 text-xs" style={{ color: 'var(--text-disabled)' }}>请检查网络后重试</p>
      <button
        onClick={onRetry}
        className="flex items-center gap-1.5 mt-4 px-4 py-2 text-sm font-medium rounded-lg transition-colors"
        style={{ background: 'var(--accent-primary)', color: '#fff' }}
      >
        <RefreshCw size={14} /> 重新连接
      </button>
    </div>
  );
}
