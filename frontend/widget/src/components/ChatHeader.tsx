import { Bot } from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import type { ConnectionStatus } from '../types';

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  connected: '在线',
  connecting: '连接中…',
  disconnected: '离线',
};
const STATUS_DOT: Record<ConnectionStatus, string> = {
  connected: 'status-dot',
  connecting: 'w-2.5 h-2.5 rounded-full bg-[#F0A050] animate-pulse mr-1.5',
  disconnected: 'w-2.5 h-2.5 rounded-full bg-[#8B95A5] mr-1.5',
};

export default function ChatHeader() {
  const connectionStatus = useChatStore((s) => s.connectionStatus);

  return (
    <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--border-default)' }}>
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 flex items-center justify-center rounded-full"
             style={{ background: 'var(--accent-primary)' }}>
          <Bot size={18} color="#fff" />
        </div>
        <div>
          <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            CogniFlow 客服助手
          </div>
        </div>
      </div>
      <div className="flex items-center gap-1 text-xs" style={{ color: 'var(--text-secondary)' }}>
        <span className={STATUS_DOT[connectionStatus]} />
        {STATUS_LABEL[connectionStatus]}
      </div>
    </div>
  );
}
