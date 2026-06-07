import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, BookOpen, Wrench, Bot, MessageSquare, BarChart3, ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';

const MENU = [
  { to: '/',           icon: LayoutDashboard, label: '仪表盘' },
  { to: '/knowledge',  icon: BookOpen,         label: '知识库' },
  { to: '/tools',      icon: Wrench,           label: '工具管理' },
  { to: '/agents',     icon: Bot,              label: 'Agent 配置' },
  { to: '/conversations', icon: MessageSquare, label: '对话记录' },
  { to: '/feedback',   icon: BarChart3,        label: '反馈看板' },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();

  return (
    <aside
      className="flex flex-col h-screen transition-all duration-200 border-r"
      style={{
        width: collapsed ? 64 : 240,
        background: '#0E1219',
        borderColor: 'var(--border-default)',
      }}
    >
      {/* Logo */}
      <div className="flex items-center h-14 px-4 border-b" style={{ borderColor: 'var(--border-default)' }}>
        <div className="w-8 h-8 flex items-center justify-center rounded"
             style={{ background: 'var(--accent-primary)', clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)' }}>
          <span className="text-xs font-bold" style={{ color: '#0A0E14' }}>C</span>
        </div>
        {!collapsed && (
          <span className="ml-2.5 text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
            CogniFlow
          </span>
        )}
      </div>

      {/* Menu */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
        {MENU.map((item) => {
          const isActive = location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to));
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className="flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-colors"
              style={{
                color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                background: isActive ? 'rgba(0,212,228,0.08)' : 'transparent',
                borderLeft: isActive ? '2px solid var(--accent-primary)' : '2px solid transparent',
              }}
            >
              <item.icon size={20} />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-center h-10 border-t hover:bg-[var(--bg-tertiary)] transition-colors"
        style={{ borderColor: 'var(--border-default)', color: 'var(--text-secondary)' }}
      >
        {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
      </button>
    </aside>
  );
}
