import { useChatStore } from '../store/chatStore';
import type { WsIncoming, WsOutgoing } from '../types';
import { useCallback, useEffect, useRef } from 'react';

const WS_URL = 'ws://localhost:8000/ws/chat';
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000];

/* ---- Mock 回复数据（后端未就绪时使用） ---- */
const MOCK_REPLIES: Record<string, { chunks: string[]; delay?: number }> = {
  default: {
    chunks: [
      '您好！我是 CogniFlow 智能客服助手，',
      '很高兴为您服务。\n\n',
      '当前系统处于 Mock 模式，后端服务尚未连接。',
      '\n\n您可以尝试以下问题：\n',
      '• 我想查一下我的订单\n',
      '• 如何申请退款？\n',
      '• 这款商品有什么规格？',
    ],
    delay: 400,
  },
  订单: {
    chunks: [
      '正在为您查询最近 30 天的订单信息…\n\n',
      '查询到以下订单：\n',
      '1. **订单 #20240601001** — 无线降噪耳机 ×1 — ¥299.00 — 已签收\n',
      '2. **订单 #20240605003** — 手机保护壳 ×2 — ¥79.80 — 运输中\n\n',
      '如需查看详情或申请售后，请直接告诉我。',
    ],
    delay: 800,
  },
  退款: {
    chunks: [
      '退款流程如下：\n\n',
      '1. 在「我的订单」中选择对应订单\n',
      '2. 点击「申请退款」并选择退款原因\n',
      '3. 提交后 1-3 个工作日内审核\n',
      '4. 审核通过后，款项 3-7 个工作日退回原支付方式\n\n',
      '需要我帮您发起退款吗？请提供您的手机号或订单号。',
    ],
    delay: 500,
  },
  物流: {
    chunks: [
      '您的订单 #20240605003 物流状态：\n\n',
      '📍 当前已到达「上海市浦东分拣中心」\n',
      '📦 预计送达时间：2024年6月8日\n',
      '🚚 承运快递：顺丰速运\n',
      '📋 运单号：SF1234567890\n\n',
      '您可以通过快递官网或 App 实时追踪物流动态。',
    ],
    delay: 600,
  },
};

function getMockReply(userMessage: string): string[] {
  if (userMessage.includes('订单')) return MOCK_REPLIES.订单.chunks;
  if (userMessage.includes('退款') || userMessage.includes('退货')) return MOCK_REPLIES.退款.chunks;
  if (userMessage.includes('物流') || userMessage.includes('快递') || userMessage.includes('到哪'))
    return MOCK_REPLIES.物流.chunks;
  return MOCK_REPLIES.default.chunks;
}

function getMockDelay(userMessage: string): number {
  if (userMessage.includes('订单')) return MOCK_REPLIES.订单.delay!;
  if (userMessage.includes('退款') || userMessage.includes('退货')) return MOCK_REPLIES.退款.delay!;
  if (userMessage.includes('物流') || userMessage.includes('快递')) return MOCK_REPLIES.物流.delay!;
  return MOCK_REPLIES.default.delay!;
}

/* ---- Hook ---- */
export function useWebSocket(mockMode = true) {
  const {
    addMessage, appendToLastBotMessage, finishStreaming,
    setSessionId, setConnectionStatus, setIsBotTyping,
    setQueuePosition, messages,
  } = useChatStore();

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempt = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

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
        case 'connected':
          setSessionId(data.sessionId);
          break;
        case 'typing':
          setIsBotTyping(true);
          break;
        case 'stream_chunk':
          appendToLastBotMessage(data.content);
          break;
        case 'stream_end':
          finishStreaming(data.messageId);
          break;
        case 'error':
          addMessage({
            id: 'err-' + Date.now(),
            role: 'system', content: `[错误] ${data.detail}`,
            createdAt: Date.now(),
          });
          setIsBotTyping(false);
          break;
        case 'handoff':
          setQueuePosition(data.queuePosition ?? null);
          addMessage({
            id: 'handoff-' + Date.now(),
            role: 'system',
            content: `正在为您转接人工客服，当前排队位置：${data.queuePosition ?? '未知'}`,
            createdAt: Date.now(),
          });
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

  const send = useCallback((content: string) => {
    const userMsgId = 'u-' + Date.now();
    addMessage({ id: userMsgId, role: 'user', content, createdAt: Date.now() });

    if (mockMode) {
      setIsBotTyping(true);
      const botMsgId = 'b-' + Date.now();
      addMessage({ id: botMsgId, role: 'bot', content: '', createdAt: Date.now(), isStreaming: true });

      const chunks = getMockReply(content);
      const delay = getMockDelay(content);
      let index = 0;

      const typeChunk = () => {
        if (index < chunks.length) {
          appendToLastBotMessage(chunks[index]);
          index++;
          timerRef.current = setTimeout(typeChunk, delay);
        } else {
          finishStreaming(botMsgId);
        }
      };
      timerRef.current = setTimeout(typeChunk, 300);
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const payload: WsOutgoing = { type: 'message', content };
      wsRef.current.send(JSON.stringify(payload));
    }
  }, [mockMode]);

  const sendFeedback = useCallback((messageId: string, rating: 'helpful' | 'unhelpful') => {
    useChatStore.getState().setFeedback(messageId, rating);
    if (!mockMode && wsRef.current?.readyState === WebSocket.OPEN) {
      const payload: WsOutgoing = { type: 'feedback', messageId, rating };
      wsRef.current.send(JSON.stringify(payload));
    }
  }, [mockMode]);

  useEffect(() => { connect(); return () => disconnect(); }, [connect, disconnect]);

  return { send, sendFeedback, connect, disconnect };
}
