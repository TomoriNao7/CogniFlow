import { LogOut, UserRound } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

export default function Header() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <header className="flex items-center justify-between h-14 px-6 border-b" style={{ borderColor: 'var(--border-default)' }}>
      <div />
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
          <UserRound size={16} />
          <span>{user?.username ?? 'Admin'}</span>
          <span className="text-xs px-2 py-0.5 rounded"
                style={{ background: 'rgba(0,212,228,0.1)', color: 'var(--accent-primary)' }}>
            {user?.role ?? 'admin'}
          </span>
        </div>
        <button onClick={logout}
                className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] transition-colors"
                style={{ color: 'var(--text-secondary)' }}>
          <LogOut size={16} />
        </button>
      </div>
    </header>
  );
}
