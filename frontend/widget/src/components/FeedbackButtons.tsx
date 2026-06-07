import { ThumbsUp, ThumbsDown } from 'lucide-react';

interface Props {
  messageId: string;
  onFeedback: (messageId: string, rating: 'helpful' | 'unhelpful') => void;
}

export default function FeedbackButtons({ messageId, onFeedback }: Props) {
  return (
    <div className="flex items-center gap-2 mt-2 pt-1.5 border-t" style={{ borderColor: 'var(--border-default)' }}>
      <button
        onClick={() => onFeedback(messageId, 'helpful')}
        className="flex items-center gap-1 text-xs px-2 py-0.5 rounded transition-colors hover:bg-black/5"
        style={{ color: 'var(--text-secondary)' }}
      >
        <ThumbsUp size={12} /> 有帮助
      </button>
      <button
        onClick={() => onFeedback(messageId, 'unhelpful')}
        className="flex items-center gap-1 text-xs px-2 py-0.5 rounded transition-colors hover:bg-black/5"
        style={{ color: 'var(--text-secondary)' }}
      >
        <ThumbsDown size={12} /> 没帮助
      </button>
    </div>
  );
}
