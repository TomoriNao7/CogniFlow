/* message — 单条消息 */
export interface Message {
  id: string;
  role: 'user' | 'bot' | 'system';
  content: string;
  createdAt: number;
  isStreaming?: boolean;
  feedback?: 'helpful' | 'unhelpful';
  intent?: string;
  trace?: Record<string, unknown>;
}

/* 后端 WebSocket → 前端 的消息协议 */
export type WsIncoming =
  | { type: 'intent'; intent: string; target_agent: string; confidence: number; classifier: string }
  | { type: 'chunk'; content: string }
  | { type: 'reply'; content: string; trace?: Record<string, unknown>; done: boolean }
  | { type: 'error'; detail: string }
  | { type: 'handoff'; reason: string; message: string };

/* 前端 → 后端 WebSocket 的消息协议 */
export interface WsOutgoing {
  message: string;
  conversation_id: number;
}

/* 会话状态 */
export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected';

export interface ChatState {
  messages: Message[];
  sessionId: string | null;
  conversationId: number;
  connectionStatus: ConnectionStatus;
  isBotTyping: boolean;
  queuePosition: number | null;
}
