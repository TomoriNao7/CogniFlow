import { MessageSquare, Users, AlertCircle, ThumbsUp, TrendingUp } from 'lucide-react';
import Card from '../components/ui/Card';
import Skeleton from '../components/ui/Skeleton';

/* Mock 数据 */
const STATS = [
  { label: '今日会话', value: '1,284', icon: MessageSquare, trend: '+12%', trendUp: true },
  { label: '活跃会话', value: '37', icon: Users, trend: '+5%', trendUp: true },
  { label: '转人工率', value: '8.2%', icon: AlertCircle, trend: '-2%', trendUp: true },
  { label: '满意度', value: '92.6%', icon: ThumbsUp, trend: '+1.5%', trendUp: true },
];

const BLIND_SPOTS = [
  { query: '怎么修改收货地址', count: 42 },
  { query: '优惠券用不了',     count: 38 },
  { query: '申请价保',        count: 31 },
  { query: '发票抬头填错了',   count: 27 },
  { query: '怎么取消订单',     count: 22 },
];

export default function Dashboard() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>仪表盘</h1>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {STATS.map((s) => (
          <Card key={s.label} accent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>{s.label}</div>
                <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{s.value}</div>
                <div className="flex items-center gap-1 mt-1 text-xs"
                     style={{ color: s.trendUp ? 'var(--accent-success)' : 'var(--accent-danger)' }}>
                  <TrendingUp size={12} /> {s.trend}
                </div>
              </div>
              <s.icon size={36} style={{ color: 'var(--border-default)' }} />
            </div>
          </Card>
        ))}
      </div>

      {/* Agent 分布 + 知识盲区 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>Agent 会话分布</h3>
          <div className="space-y-3">
            {[{ name: '售前 Agent', pct: 42, color: 'var(--accent-primary)' },
              { name: '售后 Agent', pct: 35, color: 'var(--accent-warning)' },
              { name: '售中 Agent', pct: 23, color: 'var(--accent-success)' },
            ].map((a) => (
              <div key={a.name}>
                <div className="flex justify-between text-sm mb-1">
                  <span style={{ color: 'var(--text-secondary)' }}>{a.name}</span>
                  <span style={{ color: 'var(--text-primary)' }}>{a.pct}%</span>
                </div>
                <div className="h-1.5 rounded-full" style={{ background: 'var(--bg-tertiary)' }}>
                  <div className="h-full rounded-full transition-all" style={{ width: `${a.pct}%`, background: a.color }} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>知识盲区 Top 5</h3>
          <div className="space-y-0">
            {BLIND_SPOTS.map((item, i) => (
              <div key={i} className="flex items-center justify-between py-2.5 border-b"
                   style={{ borderColor: 'var(--border-default)' }}>
                <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{item.query}</span>
                <span className="text-xs font-mono px-2 py-0.5 rounded"
                      style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>
                  {item.count} 次
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
