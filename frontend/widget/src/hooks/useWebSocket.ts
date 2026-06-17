import { useChatStore } from '../store/chatStore';
import type { WsIncoming, WsOutgoing } from '../types';
import { useCallback, useEffect, useRef } from 'react';

const WS_URL = 'ws://localhost:8000/ws/chat';
const HTTP_URL = 'http://localhost:8000/api/v1/chat';
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000];

/* ---- Hook ---- */
export function useWebSocket(mockMode = false) {
  const {
    addMessage, appendToLastBotMessage, finishStreaming,
    setSessionId, setConnectionStatus, setIsBotTyping,
    setQueuePosition, conversationId,
  } = useChatStore();

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const streamingMsgIdRef = useRef<string>('');  // track current streaming bot message

  const connect = useCallback(() => {
    if (mockMode) {
      setConnectionStatus('connected');
      setSessionId('mock-session-' + Date.now());
      return;
    }

    setConnectionStatus('connecting');
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
      reconnectAttempt.current = 0;
    };

    ws.onmessage = (event) => {
      const data: WsIncoming = JSON.parse(event.data);
      switch (data.type) {
        case 'intent':
          // Backend tells us which intent was classified
          break;

        case 'chunk':
          appendToLastBotMessage(data.content);
          break;

        case 'reply':
          // Finish the streaming bot message and replace with complete reply content
          if (streamingMsgIdRef.current) {
            finishStreaming(streamingMsgIdRef.current, data.trace, data.content);
            streamingMsgIdRef.current = '';
          }
          setIsBotTyping(false);
          break;

        case 'error':
          addMessage({
            id: 'err-' + Date.now(),
            role: 'system',
            content: `[错误] ${data.detail}`,
            createdAt: Date.now(),
          });
          setIsBotTyping(false);
          break;

        case 'handoff':
          setQueuePosition(null);
          addMessage({
            id: 'handoff-' + Date.now(),
            role: 'system',
            content: data.message,
            createdAt: Date.now(),
          });
          setIsBotTyping(false);
          break;
      }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      if (reconnectAttempt.current < RECONNECT_DELAYS.length) {
        const delay = RECONNECT_DELAYS[reconnectAttempt.current];
        reconnectAttempt.current++;
        setTimeout(connect, delay);
      }
    };

    ws.onerror = () => ws.close();
  }, [mockMode]);

  const disconnect = useCallback(() => {
    clearTimeout(timerRef.current);
    if (wsRef.current) wsRef.current.close();
    setConnectionStatus('disconnected');
  }, []);

  const send = useCallback(
    (content: string) => {
      const userMsgId = 'u-' + Date.now();
      addMessage({ id: userMsgId, role: 'user', content, createdAt: Date.now() });

      // Try WebSocket first, fall back to HTTP
      if (!mockMode && wsRef.current?.readyState === WebSocket.OPEN) {
        setIsBotTyping(true);
        const botMsgId = 'b-' + Date.now();
        streamingMsgIdRef.current = botMsgId;  // track for finishStreaming
        addMessage({
          id: botMsgId,
          role: 'bot',
          content: '',
          createdAt: Date.now(),
          isStreaming: true,
        });

        const payload: WsOutgoing = {
          message: content,
          conversation_id: conversationId,
        };
        wsRef.current.send(JSON.stringify(payload));
        return;
      }

      if (!mockMode) {
        // HTTP fallback
        sendViaHttp(content);
        return;
      }

      // Mock mode — used when backend is not running
      setIsBotTyping(true);
      const botMsgId = 'b-' + Date.now();
      addMessage({
        id: botMsgId,
        role: 'bot',
        content: '',
        createdAt: Date.now(),
        isStreaming: true,
      });

      const chunks = [
        'Mock 模式：后端未连接。',
        '\n\n请在 backend 目录运行 ',
        '`uvicorn app.main:app --reload --port 8000` ',
        '启动后端服务，然后关闭 mock 模式。',
      ];
      let index = 0;
      const typeChunk = () => {
        if (index < chunks.length) {
          appendToLastBotMessage(chunks[index]);
          index++;
          timerRef.current = setTimeout(typeChunk, 300);
        } else {
          finishStreaming(botMsgId);
        }
      };
      timerRef.current = setTimeout(typeChunk, 300);
    },
    [mockMode, conversationId]
  );

  const sendViaHttp = async (content: string) => {
    setIsBotTyping(true);
    const botMsgId = 'b-' + Date.now();
    addMessage({
      id: botMsgId,
      role: 'bot',
      content: '',
      createdAt: Date.now(),
      isStreaming: true,
    });

    try {
      const res = await fetch(HTTP_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: conversationId,
          user_id: 'user_001',
          message: content,
        }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      // Replace streaming placeholder with full reply
      const msgs = useChatStore.getState().messages;
      const lastIdx = msgs.length - 1;
      if (lastIdx >= 0 && msgs[lastIdx].id === botMsgId) {
        finishStreaming(botMsgId, data.trace);
        // Update the content directly for HTTP (no chunked streaming)
        useChatStore.setState((s) => ({
          messages: s.messages.map((m) =>
            m.id === botMsgId
              ? { ...m, content: data.reply, isStreaming: false, intent: data.intent }
              : m
          ),
          isBotTyping: false,
        }));
      }
    } catch (err: any) {
      addMessage({
        id: 'err-' + Date.now(),
        role: 'system',
        content: `[连接失败] 无法连接到后端服务 (${err.message})。请确认后端已启动。`,
        createdAt: Date.now(),
      });
      setIsBotTyping(false);
    }
  };

  const sendFeedback = useCallback(
    (messageId: string, rating: 'helpful' | 'unhelpful', reason?: string) => {
      useChatStore.getState().setFeedback(messageId, rating);
      if (!mockMode) {
        fetch('http://localhost:8000/api/v1/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message_id: parseInt(messageId, 10) || 0, rating, reason: reason || null }),
        }).catch(() => {});
      }
    },
    [mockMode]
  );

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { send, sendFeedback, connect, disconnect };
}
