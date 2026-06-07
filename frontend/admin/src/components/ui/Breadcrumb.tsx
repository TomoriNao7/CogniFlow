import { ChevronRight } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const LABELS: Record<string, string> = {
  '': '仪表盘',
  knowledge: '知识库管理',
  tools: '工具管理',
  agents: 'Agent 配置',
  conversations: '对话记录',
  feedback: '反馈看板',
};

export default function Breadcrumb() {
  const location = useLocation();
  const parts = location.pathname.split('/').filter(Boolean);

  const crumbs = [{ path: '/', label: '仪表盘' }];
  let current = '';
  parts.forEach((p) => {
    current += '/' + p;
    crumbs.push({ path: current, label: LABELS[p] || p });
  });

  if (crumbs.length <= 1) return null;

  return (
    <nav className="flex items-center gap-1.5 text-sm mb-2">
      {crumbs.map((c, i) => (
        <span key={c.path} className="flex items-center gap-1.5">
          {i > 0 && <ChevronRight size={14} style={{ color: 'var(--text-disabled)' }} />}
          {i === crumbs.length - 1 ? (
            <span style={{ color: 'var(--text-primary)' }}>{c.label}</span>
          ) : (
            <Link to={c.path} style={{ color: 'var(--text-secondary)' }} className="hover:text-[var(--accent-primary)] transition-colors">
              {c.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}
