import { useEffect, useState } from 'react';
import { Eye } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Table from '../components/ui/Table';
import Modal from '../components/ui/Modal';
import { fetchConversations, fetchConversationMessages, type ConvRow, type ConvMessages } from '../api/admin';

const STATUS_MAP: Record<string, { label: string; variant: 'success' | 'warning' | 'accent' }> = {
  active:  { label: '进行中', variant: 'accent' },
  closed:  { label: '已结束', variant: 'success' },
  handoff: { label: '已转人工', variant: 'warning' },
};

export default function Conversations() {
  const [rows, setRows] = useState<ConvRow[]>([]);
  const [detailOpen, setDetailOpen] = useState(false);
  const [msgs, setMsgs] = useState<ConvMessages | null>(null);

  useEffect(() => {
    fetchConversations().then(r => setRows(r.rows)).catch(() => {});
  }, []);

  const openDetail = (conv: ConvRow) => {
    fetchConversationMessages(conv.id).then(setMsgs).catch(() => {});
    setDetailOpen(true);
  };

  const columns = [
    { key: 'id', header: 'ID', width: '60px', render: (r: ConvRow) => <span className="font-mono text-sm">#{r.id}</span> },
    { key: 'title', header: '标题', render: (r: ConvRow) => <span className="font-medium">{r.title}</span> },
    { key: 'agent_name', header: 'Agent', render: (r: ConvRow) => <Badge variant="default">{r.agent_name}</Badge> },
    { key: 'status', header: '状态', width: '90px', render: (r: ConvRow) => {
      const s = STATUS_MAP[r.status] || { label: r.status, variant: 'default' as const };
      return <Badge variant={s.variant}>{s.label}</Badge>;
    }},
    { key: 'message_count', header: '消息', width: '60px', render: (r: ConvRow) => <span className="font-mono text-sm">{r.message_count}</span> },
    { key: 'last_message_at', header: '最后消息', width: '160px', render: (r: ConvRow) => <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.last_message_at ?? '-'}</span> },
    { key: 'actions', header: '', width: '50px', render: (r: ConvRow) => (
      <button onClick={() => openDetail(r)} className="p-1 rounded hover:bg-[var(--bg-tertiary)]" style={{ color: 'var(--text-secondary)' }}>
        <Eye size={14} />
      </button>
    )},
  ];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>对话记录</h1>
      <Card>
        {rows.length === 0 ? (
          <p className="text-sm py-8 text-center" style={{ color: 'var(--text-disabled)' }}>暂无对话记录，通过 Widget 或 Agent 测试发送消息后刷新页面</p>
        ) : (
          <Table columns={columns} data={rows} />
        )}
      </Card>

      <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title="对话回放" width="700px">
        {msgs?.messages?.length ? (
          <div className="flex flex-col gap-3 max-h-96 overflow-y-auto">
            {msgs.messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className="max-w-[75%] px-3 py-2 rounded text-sm whitespace-pre-wrap" style={{
                  background: m.role === 'user' ? 'var(--accent-primary)' : 'var(--bg-tertiary)',
                  color: m.role === 'user' ? '#0A0E14' : 'var(--text-primary)',
                  borderRadius: m.role === 'user' ? '12px 4px 12px 12px' : '4px 12px 12px 12px',
                }}>
                  {m.content}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm py-8 text-center" style={{ color: 'var(--text-disabled)' }}>加载中…</p>
        )}
      </Modal>
    </div>
  );
}
