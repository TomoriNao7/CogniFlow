import { ThumbsUp, ThumbsDown } from 'lucide-react';

interface Props {
  messageId: string;
  onFeedback: (messageId: string, rating: 'helpful' | 'unhelpful') => void;
}

export default function FeedbackButtons({ messageId, onFeedback }: Props) {
  return (
    <div
      className="flex items-center gap-3 mt-2 pt-1.5"
      style={{ borderTop: '1px solid var(--border-default)' }}
    >
      <button
        onClick={() => onFeedback(messageId, 'helpful')}
        className="flex items-center gap-1.5 text-xs px-2 py-0.5 transition-all duration-150"
        style={{
          color: 'var(--text-secondary)',
          borderRadius: 'var(--radius-sm)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = 'var(--accent-success)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = 'var(--text-secondary)';
        }}
      >
        <ThumbsUp size={12} />
        <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>有帮助</span>
      </button>
      <button
        onClick={() => onFeedback(messageId, 'unhelpful')}
        className="flex items-center gap-1.5 text-xs px-2 py-0.5 transition-all duration-150"
        style={{
          color: 'var(--text-secondary)',
          borderRadius: 'var(--radius-sm)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = 'var(--accent-danger)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = 'var(--text-secondary)';
        }}
      >
        <ThumbsDown size={12} />
        <span style={{ fontFamily: "'JetBrains Mono', monospace" }}>没帮助</span>
      </button>
    </div>
  );
}
