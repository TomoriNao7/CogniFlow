import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, CheckCircle2, XCircle, Wrench } from 'lucide-react';
import { sendMessage, healthCheck, listTools, type ChatResponse, type ToolInfo } from '../api/chat';
import Card from './ui/Card';
import Button from './ui/Button';

interface TestMessage {
  role: 'user' | 'bot' | 'system';
  content: string;
  intent?: string;
  trace?: Record<string, unknown> | null;
}

export default function AgentTest() {
  const [messages, setMessages] = useState<TestMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [conversationId, setConversationId] = useState(Date.now());
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    checkBackend();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const checkBackend = async () => {
    setBackendStatus('checking');
    try {
      const health = await healthCheck();
      if (health.status === 'ok') {
        setBackendStatus('online');
        const t = await listTools();
        setTools(t.tools);
      } else {
        setBackendStatus('offline');
      }
    } catch {
      setBackendStatus('offline');
    }
  };

  const handleSend = async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setLoading(true);

    try {
      const res: ChatResponse = await sendMessage(conversationId, msg);
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          content: res.reply,
          intent: res.intent,
          trace: res.trace,
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'system', content: `请求失败: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
          <Wrench size={16} className="inline mr-2" />
          Agent 测试（售前 + 售中）
        </h3>
        <div className="flex items-center gap-3">
          {backendStatus === 'checking' ? (
            <span className="text-xs flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
              <Loader2 size={12} className="animate-spin" /> 检测中
            </span>
          ) : backendStatus === 'online' ? (
            <span className="text-xs flex items-center gap-1" style={{ color: 'var(--accent-success)' }}>
              <CheckCircle2 size={12} /> 后端在线 ({tools.length} 个工具)
            </span>
          ) : (
            <span className="text-xs flex items-center gap-1" style={{ color: 'var(--accent-danger)' }}>
              <XCircle size={12} /> 后端离线
            </span>
          )}
          <Button onClick={checkBackend} size="sm">
            重检
          </Button>
          <Button onClick={() => { setMessages([]); setConversationId(Date.now()); }} size="sm">
            清空
          </Button>
        </div>
      </div>

      {/* Messages area */}
      <div
        className="mb-3 rounded-lg overflow-y-auto"
        style={{
          height: '300px',
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-default)',
          padding: '12px',
        }}
      >
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-sm" style={{ color: 'var(--text-secondary)' }}>
            输入消息测试 Agent — 售前：商品咨询/库存/优惠券/会员；售中：订单支付/地址/发票
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className="mb-3">
            <div className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>
              {m.role === 'user' ? '你' : m.role === 'bot' ? (m.intent === 'place_order' ? '售中 Agent' : '售前 Agent') : '系统'}
              {m.intent && (
                <span className="ml-2 px-1.5 py-0.5 rounded text-xs"
                      style={{ background: 'var(--bg-tertiary)', color: 'var(--accent-primary)' }}>
                  {m.intent}
                </span>
              )}
            </div>
            <div
              className="text-sm whitespace-pre-wrap rounded-lg p-3"
              style={{
                background: m.role === 'user' ? 'var(--accent-primary)' : 'var(--bg-primary)',
                color: m.role === 'user' ? '#fff' : 'var(--text-primary)',
                border: m.role === 'user' ? 'none' : '1px solid var(--border-default)',
              }}
            >
              {m.content}
            </div>
            {m.trace && (
              <details className="mt-1">
                <summary className="text-xs cursor-pointer" style={{ color: 'var(--text-secondary)' }}>
                  追踪信息
                </summary>
                <pre className="text-xs mt-1 p-2 rounded overflow-x-auto" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>
                  {JSON.stringify(m.trace, null, 2)}
                </pre>
              </details>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
            <Loader2 size={14} className="animate-spin" /> Agent 思考中...
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入测试消息（售前/售中）..."
          disabled={backendStatus !== 'online'}
          className="flex-1 px-3 py-2 rounded-lg text-sm border outline-none disabled:opacity-50"
          style={{
            background: 'var(--bg-primary)',
            color: 'var(--text-primary)',
            borderColor: 'var(--border-default)',
          }}
        />
        <Button onClick={handleSend} disabled={loading || backendStatus !== 'online'}>
          <Send size={14} className="mr-1" /> 发送
        </Button>
      </div>

      {/* Quick test buttons */}
      <div className="flex gap-2 mt-3 flex-wrap">
        {[
          /* 售前 */
          'iPhone 15 Pro 多少钱？',
          '现在有什么优惠活动？',
          '帮我查一下库存',
          'PLUS 会员有什么权益？',
          /* 售中 */
          '我的订单支付失败怎么办？',
          '帮我查一下未支付订单',
          '我想修改收货地址',
          '帮我开一张发票',
        ].map((q) => (
          <button
            key={q}
            onClick={() => setInput(q)}
            disabled={backendStatus !== 'online'}
            className="text-xs px-2 py-1 rounded-full border transition-colors hover:bg-[var(--accent-primary)] hover:text-white disabled:opacity-50"
            style={{
              background: 'var(--bg-secondary)',
              color: 'var(--text-secondary)',
              borderColor: 'var(--border-default)',
            }}
          >
            {q}
          </button>
        ))}
      </div>
    </Card>
  );
}
