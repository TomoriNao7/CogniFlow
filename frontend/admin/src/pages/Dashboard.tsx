import { useEffect, useState } from 'react';
import { MessageSquare, Users, AlertCircle, ThumbsUp, TrendingUp } from 'lucide-react';
import Card from '../components/ui/Card';
import AgentTest from '../components/AgentTest';
import { fetchDashboard, type DashboardStats } from '../api/admin';

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    fetchDashboard().then(setStats).catch(() => {});
  }, []);

  const STATS = [
    { label: '今日会话', value: stats?.today_conversations?.toLocaleString() ?? '-', icon: MessageSquare, trend: '', trendUp: true },
    { label: '活跃会话', value: stats?.active_conversations?.toLocaleString() ?? '-', icon: Users, trend: '', trendUp: true },
    { label: '转人工数', value: stats?.handoff_count?.toLocaleString() ?? '-', icon: AlertCircle, trend: '', trendUp: false },
    { label: '满意度', value: stats ? `${stats.satisfaction}%` : '-', icon: ThumbsUp, trend: '', trendUp: true },
  ];

  const dist = stats?.agent_distribution ?? [];
  const total = dist.reduce((s, a) => s + a.count, 0) || 1;

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>仪表盘</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {STATS.map((s) => (
          <Card key={s.label} accent>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>{s.label}</div>
                <div className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>{s.value}</div>
                {s.trend && (
                  <div className="flex items-center gap-1 mt-1 text-xs"
                       style={{ color: s.trendUp ? 'var(--accent-success)' : 'var(--accent-danger)' }}>
                    <TrendingUp size={12} /> {s.trend}
                  </div>
                )}
              </div>
              <s.icon size={36} style={{ color: 'var(--border-default)' }} />
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>Agent 会话分布</h3>
          <div className="space-y-3">
            {dist.map((a) => (
              <div key={a.name}>
                <div className="flex justify-between text-sm mb-1">
                  <span style={{ color: 'var(--text-secondary)' }}>{a.name}</span>
                  <span style={{ color: 'var(--text-primary)' }}>{Math.round(a.count / total * 100)}%</span>
                </div>
                <div className="h-1.5 rounded-full" style={{ background: 'var(--bg-tertiary)' }}>
                  <div className="h-full rounded-full" style={{
                    width: `${Math.round(a.count / total * 100)}%`,
                    background: a.name.includes('售前') ? 'var(--accent-primary)' :
                                a.name.includes('售后') ? 'var(--accent-warning)' : 'var(--accent-success)',
                  }} />
                </div>
              </div>
            ))}
            {dist.length === 0 && <p className="text-sm" style={{ color: 'var(--text-disabled)' }}>暂无数据</p>}
          </div>
        </Card>

        <Card>
          <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>系统状态</h3>
          <div className="space-y-3">
            {[
              { label: '总会话数', value: stats?.total_conversations?.toLocaleString() ?? '-' },
              { label: '总消息数', value: stats?.total_messages?.toLocaleString() ?? '-' },
              { label: '反馈总数', value: stats?.total_feedback?.toLocaleString() ?? '-' },
            ].map((item) => (
              <div key={item.label} className="flex justify-between py-2 border-b" style={{ borderColor: 'var(--border-default)' }}>
                <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
                <span className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>{item.value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <AgentTest />
    </div>
  );
}
