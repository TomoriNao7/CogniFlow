import { useChatStore } from '../store/chatStore';
import { useWebSocket } from '../hooks/useWebSocket';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import QuickReply from './QuickReply';
import ConnectionError from './ConnectionError';

export default function ChatWidget() {
  const { send, sendFeedback, connect } = useWebSocket(false);
  const connectionStatus = useChatStore((s) => s.connectionStatus);
  const messages = useChatStore((s) => s.messages);

  return (
    <div
      className="widget-theme flex flex-col w-full h-full overflow-hidden ark-corner"
      style={{
        background: 'var(--bg-primary)',
        boxShadow: 'var(--shadow-md)',
      }}
    >
      <ChatHeader />
      {connectionStatus === 'disconnected' && messages.length > 0 ? (
        <ConnectionError onRetry={connect} />
      ) : (
        <MessageList onFeedback={sendFeedback} />
      )}
      {messages.length === 0 && <QuickReply onSend={send} />}
      <ChatInput onSend={send} disabled={connectionStatus === 'disconnected'} />
    </div>
  );
}
