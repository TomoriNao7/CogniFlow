import { Hexagon } from 'lucide-react';
import { useChatStore } from '../store/chatStore';
import type { ConnectionStatus } from '../types';

const STATUS_LABEL: Record<ConnectionStatus, string> = {
  connected: 'ONLINE',
  connecting: 'CONNECTING…',
  disconnected: 'OFFLINE',
};

export default function ChatHeader() {
  const connectionStatus = useChatStore((s) => s.connectionStatus);

  return (
    <div
      className="flex items-center justify-between px-4 py-3 ark-header-cut"
      style={{
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-default)',
      }}
    >
      {/* 左侧：Logo + 标题 */}
      <div className="flex items-center gap-3">
        {/* 六角形图标容器 */}
        <div
          className="w-9 h-9 flex items-center justify-center"
          style={{
            background: 'var(--accent-primary)',
            clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)',
          }}
        >
          <Hexagon size={16} color="#E0D8CC" fill="none" strokeWidth={2.5} />
        </div>
        <div>
          <div
            className="text-sm font-bold tracking-wider"
            style={{ color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}
          >
            [ CogniFlow ]
          </div>
          <div className="text-xs tracking-wide" style={{ color: 'var(--accent-primary)' }}>
            智能客服助手
          </div>
        </div>
      </div>

      {/* 右侧：连接状态 */}
      <div className="flex items-center gap-2 text-xs" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
        <span
          className="status-dot"
          style={{
            background:
              connectionStatus === 'connected' ? 'var(--accent-success)' :
              connectionStatus === 'connecting' ? 'var(--accent-glow)' :
              'var(--text-disabled)',
          }}
        />
        <span style={{ color: 'var(--text-secondary)' }}>
          {STATUS_LABEL[connectionStatus]}
        </span>
      </div>
    </div>
  );
}
