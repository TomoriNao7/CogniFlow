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
    <div className="flex-1 overflow-y-auto px-3 py-4 space-y-3 widget-scrollbar">
      {messages.length === 0 && !isBotTyping && (
        <div className="flex flex-col items-center justify-center h-full gap-2" style={{ color: 'var(--text-secondary)' }}>
          <div className="text-4xl mb-2">
            {connectionStatus === 'connected' ? '👋' : '🔌'}
          </div>
          <div className="text-sm font-medium">
            {connectionStatus === 'connected'
              ? '你好！我是 CogniFlow 智能客服'
              : '正在连接服务器…'}
          </div>
          <div className="text-xs">
            {connectionStatus === 'connected'
              ? '有什么可以帮你的？请直接输入问题，或点击下方快捷标签。'
              : '请稍候，首次连接可能需要几秒钟'}
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
