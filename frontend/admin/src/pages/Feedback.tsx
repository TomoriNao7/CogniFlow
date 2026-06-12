import { useEffect, useState } from 'react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Table from '../components/ui/Table';
import { fetchFeedback, fetchFeedbackStats, type FbRow, type FbStats } from '../api/admin';

export default function Feedback() {
  const [rows, setRows] = useState<FbRow[]>([]);
  const [stats, setStats] = useState<FbStats | null>(null);

  useEffect(() => {
    fetchFeedback().then(r => setRows(r.rows)).catch(() => {});
    fetchFeedbackStats().then(setStats).catch(() => {});
  }, []);

  const columns = [
    { key: 'message_id', header: '消息', width: '70px', render: (r: FbRow) => <span className="font-mono text-sm">#{r.message_id}</span> },
    { key: 'rating', header: '评价', width: '80px', render: (r: FbRow) =>
      r.rating === 'helpful' ? <Badge variant="success">有帮助</Badge> : <Badge variant="danger">没帮助</Badge>
    },
    { key: 'reason', header: '原因', render: (r: FbRow) => <span style={{ color: r.reason ? 'var(--text-primary)' : 'var(--text-disabled)' }}>{r.reason || '(未填写)'}</span> },
    { key: 'review_status', header: '复核', width: '80px', render: (r: FbRow) =>
      r.review_status === 'pending' ? <Badge variant="warning">待复核</Badge> : <Badge variant="success">已复核</Badge>
    },
    { key: 'created_at', header: '时间', width: '160px', render: (r: FbRow) => <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{r.created_at ?? '-'}</span> },
  ];

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>反馈看板</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: '好评率', value: stats ? `${stats.satisfaction_rate}%` : '-', color: 'var(--accent-success)' },
          { label: '待复核', value: stats?.pending_review?.toString() ?? '-', color: 'var(--accent-warning)' },
          { label: '总反馈', value: stats?.total?.toString() ?? '-', color: 'var(--accent-primary)' },
        ].map((s) => (
          <Card key={s.label} accent>
            <div className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>{s.label}</div>
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
          </Card>
        ))}
      </div>

      <Card>
        <div className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>反馈列表</div>
        {rows.length === 0 ? (
          <p className="text-sm py-8 text-center" style={{ color: 'var(--text-disabled)' }}>暂无反馈数据</p>
        ) : (
          <Table columns={columns} data={rows} />
        )}
      </Card>
    </div>
  );
}
