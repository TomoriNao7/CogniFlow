import { useState } from 'react';
import { Eye } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Table from '../components/ui/Table';
import Modal from '../components/ui/Modal';

interface ConvRow { id: number; userNickname: string; agentName: string; status: string; title: string; messageCount: number; satisfaction?: string; lastMessageAt: string; }

const MOCK: ConvRow[] = [
  { id: 1, userNickname: '用户***23', agentName: '售后客服', status: 'closed', title: '申请退款', messageCount: 8, satisfaction: 'helpful', lastMessageAt: '2024-06-07 14:23' },
  { id: 2, userNickname: '用户***88', agentName: '售后客服', status: 'handoff', title: '投诉商品质量', messageCount: 12, lastMessageAt: '2024-06-07 14:15' },
  { id: 3, userNickname: '用户***56', agentName: '售前客服', status: 'closed', title: '咨询商品规格', messageCount: 5, satisfaction: 'unhelpful', lastMessageAt: '2024-06-07 13:50' },
  { id: 4, userNickname: '用户***01', agentName: '售中客服', status: 'active', title: '支付失败', messageCount: 3, lastMessageAt: '2024-06-07 14:30' },
];

const STATUS_MAP: Record<string, { label: string; variant: 'success' | 'warning' | 'accent' }> = {
  active:  { label: '进行中', variant: 'accent' },
  closed:  { label: '已结束', variant: 'success' },
  handoff: { label: '已转人工', variant: 'warning' },
};

export default function Conversations() {
  const [detailOpen, setDetailOpen] = useState(false);
  const [activeConv, setActiveConv] = useState<ConvRow | null>(null);

  const columns = [
    { key: 'userNickname', header: '用户', render: (r: ConvRow) => <span>{r.userNickname}</span> },
    { key: 'title', header: '会话摘要', render: (r: ConvRow) => <span className="font-medium">{r.title}</span> },
    { key: 'agentName', header: 'Agent', render: (r: ConvRow) => <Badge variant="default">{r.agentName}</Badge> },
    { key: 'status', header: '状态', width: '90px', render: (r: ConvRow) => {
      const s = STATUS_MAP[r.status] || { label: r.status, variant: 'default' as const };
      return <Badge variant={s.variant}>{s.label}</Badge>;
    }},
    { key: 'messageCount', header: '消息数', width: '70px', render: (r: ConvRow) => <span className="font-mono text-sm">{r.messageCount}</span> },
    { key: 'satisfaction', header: '满意度', width: '80px', render: (r: ConvRow) => r.satisfaction === 'helpful' ? <Badge variant="success">👍</Badge> : r.satisfaction === 'unhelpful' ? <Badge variant="danger">👎</Badge> : <span style={{ color: 'var(--text-disabled)' }}>-</span> },
    { key: 'lastMessageAt', header: '最后消息', width: '140px', render: (r: ConvRow) => <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.lastMessageAt}</span> },
    { key: 'actions', header: '', width: '50px', render: (r: ConvRow) => (
      <button onClick={() => { setActiveConv(r); setDetailOpen(true); }}
              className="p-1 rounded hover:bg-[var(--bg-tertiary)]" style={{ color: 'var(--text-secondary)' }}>
        <Eye size={14} />
      </button>
    )},
  ];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>对话记录</h1>
      <Card><Table columns={columns} data={MOCK} /></Card>

      <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title={`会话 #${activeConv?.id} ${activeConv?.title ?? ''}`} width="700px">
        {activeConv && (
          <div className="flex flex-col gap-3">
            {[
              { role: 'user', text: '你好，我想申请退款' },
              { role: 'bot',   text: '您好！我可以帮您处理退款。请提供您的手机号，方便我查询订单。' },
              { role: 'user', text: '13812345678' },
              { role: 'bot',   text: '已查到您的近期订单。请问哪一笔需要退款？\n\n1. 订单 #20240601001 — 无线降噪耳机 — ¥299.00\n2. 订单 #20240605003 — 手机保护壳 — ¥79.80' },
              { role: 'user', text: '第一个' },
              { role: 'bot',   text: '好的，已为您申请订单 #20240601001 的退款。款项将在 3-7 个工作日内退回原支付方式。如有其他问题随时联系我。' },
            ].map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className="max-w-[75%] px-3 py-2 rounded text-sm" style={{
                  background: m.role === 'user' ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                  color: m.role === 'user' ? '#0A0E14' : 'var(--text-primary)',
                  borderRadius: m.role === 'user' ? '12px 4px 12px 12px' : '4px 12px 12px 12px',
                }}>
                  {m.text}
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
}
