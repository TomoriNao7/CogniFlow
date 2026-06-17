import { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';

interface Props {
  messageId: string;
  onFeedback: (messageId: string, rating: 'helpful' | 'unhelpful', reason?: string) => void;
}

export default function FeedbackButtons({ messageId, onFeedback }: Props) {
  const [showReason, setShowReason] = useState(false);
  const [reason, setReason] = useState('');

  const handleUnhelpful = () => {
    setShowReason(true);
  };

  const submitReason = () => {
    onFeedback(messageId, 'unhelpful', reason || undefined);
    setShowReason(false);
    setReason('');
  };

  return (
    <div>
      {!showReason ? (
        <div
          className="flex items-center gap-3 mt-2 pt-1.5"
          style={{ borderTop: '1px solid var(--border-default)' }}
        >
          <button
            onClick={() => onFeedback(messageId, 'helpful')}
            className="flex items-center gap-1.5 text-xs px-2 py-0.5 transition-all duration-150"
            style={{ color: 'var(--text-secondary)', borderRadius: 'var(--radius-sm)' }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent-success)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-secondary)'; }}
          >
            <ThumbsUp size={12} />
            <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>有帮助</span>
          </button>
          <button
            onClick={handleUnhelpful}
            className="flex items-center gap-1.5 text-xs px-2 py-0.5 transition-all duration-150"
            style={{ color: 'var(--text-secondary)', borderRadius: 'var(--radius-sm)' }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--accent-danger)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-secondary)'; }}
          >
            <ThumbsDown size={12} />
            <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>没帮助</span>
          </button>
        </div>
      ) : (
        <div className="mt-2 pt-1.5" style={{ borderTop: '1px solid var(--border-default)' }}>
          <p className="text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>哪里不好？</p>
          <div className="flex gap-1.5">
            <input
              autoFocus
              value={reason}
              onChange={e => setReason(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') submitReason(); }}
              placeholder="请简单描述…"
              className="flex-1 px-2 py-1 text-xs rounded outline-none"
              style={{
                background: 'var(--bg-tertiary)',
                border: '1px solid var(--border-default)',
                color: 'var(--text-primary)',
              }}
            />
            <button
              onClick={submitReason}
              className="px-2 py-1 text-xs rounded transition-colors"
              style={{
                background: 'var(--accent-primary)',
                color: '#1A1A28',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              提交
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
