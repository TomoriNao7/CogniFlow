import type { Message } from '../types';
import FeedbackButtons from './FeedbackButtons';

interface Props {
  message: Message;
  onFeedback?: (messageId: string, rating: 'helpful' | 'unhelpful') => void;
}

/* 简单的 Markdown 行内渲染 */
function renderContent(text: string) {
  return text
    .split('\n')
    .map((line, i) => {
      const bolded = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      return <span key={i} dangerouslySetInnerHTML={{ __html: bolded + '<br/>' }} />;
    });
}

export default function ChatBubble({ message, onFeedback }: Props) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  /* 系统消息 */
  if (isSystem) {
    return (
      <div className="flex justify-center animate-bubble-in">
        <div className="text-xs px-3 py-1.5 rounded-full max-w-[85%] text-center"
             style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}>
          {message.content}
        </div>
      </div>
    );
  }

  /* Bot / User 气泡 */
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-bubble-in`}>
      <div
        className="max-w-[80%] px-3.5 py-2.5 text-sm leading-relaxed break-words"
        style={{
          background: isUser ? 'var(--bg-user-bubble)' : 'var(--bg-bot-bubble)',
          color: isUser ? '#FFFFFF' : 'var(--text-primary)',
          borderRadius: isUser ? '12px 4px 12px 12px' : '4px 12px 12px 12px',
        }}
      >
        {renderContent(message.content)}
        {message.isStreaming && (
          <span className="inline-block w-1.5 h-4 ml-0.5 align-text-bottom cursor-blink"
                style={{ background: isUser ? '#fff' : 'var(--accent-primary)' }} />
        )}
        {!isUser && !message.isStreaming && !message.feedback && (
          <FeedbackButtons messageId={message.id} onFeedback={onFeedback!} />
        )}
        {!isUser && message.feedback && (
          <div className="mt-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
            {message.feedback === 'helpful' ? '✓ 感谢反馈' : '✗ 已记录，我们会改进'}
          </div>
        )}
      </div>
    </div>
  );
}
