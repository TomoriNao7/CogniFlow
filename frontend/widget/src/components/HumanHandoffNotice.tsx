import { UserRound } from 'lucide-react';
import { useChatStore } from '../store/chatStore';

export default function HumanHandoffNotice() {
  const queuePosition = useChatStore((s) => s.queuePosition);

  return (
    <div className="flex justify-center">
      <div
        className="flex items-center gap-2 px-4 py-2.5 text-sm animate-bubble-in max-w-[85%]"
        style={{
          background: 'rgba(208, 120, 40, 0.1)',
          color: 'var(--accent-glow)',
          border: '1px solid var(--border-accent)',
          borderRadius: 'var(--radius-sm)',
          fontFamily: "'JetBrains Mono', monospace",
        }}
      >
        <UserRound size={14} />
        <span>
          已为您转接人工客服
          {queuePosition != null && `，排队中（前方 ${queuePosition} 人）`}
          ，请耐心等待。
        </span>
      </div>
    </div>
  );
}
