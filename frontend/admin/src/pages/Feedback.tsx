import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Table from '../components/ui/Table';

interface FbRow { id: number; messageId: number; conversationId: number; rating: string; reason: string | null; reviewStatus: string; createdAt: string; }

const MOCK: FbRow[] = [
  { id: 1, messageId: 23, conversationId: 1, rating: 'unhelpful', reason: '没有回答我的问题', reviewStatus: 'pending', createdAt: '2024-06-07 14:23' },
  { id: 2, messageId: 18, conversationId: 3, rating: 'unhelpful', reason: null, reviewStatus: 'pending', createdAt: '2024-06-07 13:50' },
  { id: 3, messageId: 15, conversationId: 1, rating: 'helpful',   reason: null, reviewStatus: 'reviewed', createdAt: '2024-06-07 14:20' },
];

export default function Feedback() {
  const columns = [
    { key: 'conversationId', header: '会话', width: '70px', render: (r: FbRow) => <span className="font-mono text-sm">#{r.conversationId}</span> },
    { key: 'rating', header: '评价', width: '80px', render: (r: FbRow) => r.rating === 'helpful' ? <Badge variant="success">有帮助</Badge> : <Badge variant="danger">没帮助</Badge> },
    { key: 'reason', header: '原因', render: (r: FbRow) => <span style={{ color: r.reason ? 'var(--text-primary)' : 'var(--text-disabled)' }}>{r.reason || '(未填写)'}</span> },
    { key: 'reviewStatus', header: '复核状态', width: '90px', render: (r: FbRow) => r.reviewStatus === 'pending' ? <Badge variant="warning">待复核</Badge> : <Badge variant="success">已复核</Badge> },
    { key: 'createdAt', header: '时间', width: '140px', render: (r: FbRow) => <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.createdAt}</span> },
  ];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>反馈看板</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: '好评率', value: '92.6%', color: 'var(--accent-success)' },
          { label: '待复核', value: '12',     color: 'var(--accent-warning)' },
          { label: '知识盲区', value: '5',    color: 'var(--accent-danger)' },
        ].map((s) => (
          <Card key={s.label} accent>
            <div className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>{s.label}</div>
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
          </Card>
        ))}
      </div>

      <Card>
        <div className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>低分反馈列表</div>
        <Table columns={columns} data={MOCK} />
      </Card>
    </div>
  );
}
