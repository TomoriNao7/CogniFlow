import { useChatStore } from '../store/chatStore';
import { useAutoScroll } from '../hooks/useAutoScroll';
import ChatBubble from './ChatBubble';
import TypingIndicator from './TypingIndicator';

interface Props {
  onFeedback: (messageId: string, rating: 'helpful' | 'unhelpful') => void;
}

export default function MessageList({ onFeedback }: Props) {
  const messages = useChatStore((s) => s.messages);
  const isBotTyping = useChatStore((s) => s.isBotTyping);
  const bottomRef = useAutoScroll();
  const connectionStatus = useChatStore((s) => s.connectionStatus);

  return (
    <div
      className="flex-1 overflow-y-auto px-3 py-4 space-y-3 widget-scrollbar"
      style={{ background: 'var(--bg-primary)' }}
    >
      {messages.length === 0 && !isBotTyping && (
        <div
          className="flex flex-col items-center justify-center h-full gap-3"
          style={{ color: 'var(--text-secondary)' }}
        >
          <div
            className="w-16 h-16 flex items-center justify-center"
            style={{
              background: 'var(--bg-tertiary)',
              clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
              border: '1px solid var(--border-default)',
            }}
          >
            <span className="text-2xl" style={{ color: 'var(--accent-primary)' }}>◆</span>
          </div>
          <div
            className="text-sm font-bold tracking-wider"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              color: 'var(--accent-primary)',
            }}
          >
            {connectionStatus === 'connected'
              ? '[ 系统就绪 ] 您好，有什么可以帮您？'
              : '[ 建立连接中… ]'}
          </div>
          <div className="text-xs tracking-wide" style={{ color: 'var(--text-secondary)' }}>
            {connectionStatus === 'connected'
              ? '请直接输入问题，或点击下方快捷标签。'
              : '正在连接 CogniFlow 服务…'}
          </div>
        </div>
      )}
      {messages.map((msg) => (
        <ChatBubble key={msg.id} message={msg} onFeedback={onFeedback} />
      ))}
      {isBotTyping && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
