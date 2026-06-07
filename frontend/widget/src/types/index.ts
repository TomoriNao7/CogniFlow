/* message — 单条消息 */
export interface Message {
  id: string;
  role: 'user' | 'bot' | 'system';
  content: string;
  createdAt: number;
  isStreaming?: boolean;       // 是否正在流式输出中
  feedback?: 'helpful' | 'unhelpful';
}

/* WebSocket 收发的 JSON 消息协议 */
export type WsIncoming =
  | { type: 'connected'; sessionId: string }
  | { type: 'typing' }
  | { type: 'stream_chunk'; content: string }
  | { type: 'stream_end'; messageId: string }
  | { type: 'error'; code: string; detail: string }
  | { type: 'handoff'; reason: string; queuePosition?: number };

export type WsOutgoing =
  | { type: 'message'; content: string }
  | { type: 'feedback'; messageId: string; rating: 'helpful' | 'unhelpful' };

/* 会话状态 */
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected';

export interface ChatState {
  messages: Message[];
  sessionId: string | null;
  connectionStatus: ConnectionStatus;
  isBotTyping: boolean;
  queuePosition: number | null;
}
