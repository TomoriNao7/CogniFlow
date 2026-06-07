import { create } from 'zustand';
import type { ChatState, Message } from '../types';

interface ChatActions {
  addMessage: (msg: Message) => void;
  appendToLastBotMessage: (chunk: string) => void;
  finishStreaming: (messageId: string) => void;
  setFeedback: (messageId: string, rating: 'helpful' | 'unhelpful') => void;
  setSessionId: (id: string) => void;
  setConnectionStatus: (status: ChatState['connectionStatus']) => void;
  setIsBotTyping: (typing: boolean) => void;
  setQueuePosition: (pos: number | null) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState & ChatActions>((set) => ({
  messages: [],
  sessionId: null,
  connectionStatus: 'disconnected',
  isBotTyping: false,
  queuePosition: null,

  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  appendToLastBotMessage: (chunk) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'bot' && last.isStreaming) {
        msgs[msgs.length - 1] = { ...last, content: last.content + chunk };
      }
      return { messages: msgs };
    }),

  finishStreaming: (messageId) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === messageId ? { ...m, isStreaming: false } : m
      ),
      isBotTyping: false,
    })),

  setFeedback: (messageId, rating) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === messageId ? { ...m, feedback: rating } : m
      ),
    })),

  setSessionId: (id) => set({ sessionId: id }),
  setConnectionStatus: (status) => set({ connectionStatus: status }),
  setIsBotTyping: (typing) => set({ isBotTyping: typing }),
  setQueuePosition: (pos) => set({ queuePosition: pos }),
  clearMessages: () => set({ messages: [] }),
}));
