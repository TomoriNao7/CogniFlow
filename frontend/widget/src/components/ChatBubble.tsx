import type { Message } from '../types';
import FeedbackButtons from './FeedbackButtons';

/* 简单的 Markdown 行内渲染 */
function renderContent(text: string) {
  return text
    .split('\n')
    .map((line, i) => {
      const bolded = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      return <span key={i} dangerouslySetInnerHTML={{ __html: bolded + '<br/>' }} />;
    });
}

export default function ChatBubble({ message, onFeedback }: {
  message: Message;
  onFeedback?: (messageId: string, rating: 'helpful' | 'unhelpful') => void;
}) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  /* 系统消息 — 等宽括号风格 */
  if (isSystem) {
    return (
      <div className="flex justify-center animate-bubble-in">
        <div
          className="text-xs px-3 py-1.5 max-w-[85%] text-center tracking-wide"
          style={{
            background: 'var(--bg-tertiary)',
            color: 'var(--accent-cyan)',
            borderRadius: 'var(--radius-sm)',
            fontFamily: "'JetBrains Mono', monospace",
            border: '1px solid var(--border-default)',
          }}
        >
          [ {message.content} ]
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
          color: isUser ? '#F5F0E8' : 'var(--text-primary)',
          borderRadius: isUser
            ? 'var(--radius-lg) var(--radius-sm) var(--radius-lg) var(--radius-lg)'
            : 'var(--radius-sm) var(--radius-lg) var(--radius-lg) var(--radius-lg)',
          border: isUser ? 'none' : '1px solid var(--border-default)',
          position: 'relative',
        }}
      >
        {/* Bot 气泡左上角小三角装饰 */}
        {!isUser && (
          <div
            style={{
              position: 'absolute',
              top: 0, left: 0,
              width: 0, height: 0,
              borderLeft: '6px solid var(--accent-primary)',
              borderBottom: '6px solid transparent',
            }}
          />
        )}

        {renderContent(message.content)}

        {/* 流式光标 */}
        {message.isStreaming && (
          <span
            className="inline-block w-1.5 h-4 ml-0.5 align-text-bottom cursor-blink"
            style={{ background: isUser ? '#F5F0E8' : 'var(--accent-primary)' }}
          />
        )}

        {/* 反馈按钮 */}
        {!isUser && !message.isStreaming && !message.feedback && (
          <FeedbackButtons messageId={message.id} onFeedback={onFeedback!} />
        )}
        {!isUser && message.feedback && (
          <div className="mt-2 text-xs" style={{
            color: message.feedback === 'helpful' ? 'var(--accent-success)' : 'var(--accent-danger)',
          }}>
            {message.feedback === 'helpful' ? '✓ 感谢反馈' : '✗ 已记录，我们会改进'}
          </div>
        )}
      </div>
    </div>
  );
}
