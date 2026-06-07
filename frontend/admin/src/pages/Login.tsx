import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bot, Eye, EyeOff } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [error, setError] = useState('');
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const ok = await login(username, password);
    if (ok) navigate('/');
    else setError('登录失败，请检查用户名和密码');
  };

  return (
    <div className="min-h-screen flex items-center justify-center geo-bg">
      <div className="card" style={{ width: '400px' }}>
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 flex items-center justify-center rounded-full mb-4 animate-glow-pulse"
               style={{ background: 'var(--accent-primary)' }}>
            <Bot size={28} color="#0A0E14" />
          </div>
          <h1 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>CogniFlow</h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>电商智能客服管理平台</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>用户名</label>
            <input
              value={username} onChange={(e) => setUsername(e.target.value)}
              className="px-3 py-2.5 text-sm rounded transition-colors"
              style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}
              placeholder="请输入用户名" autoFocus
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>密码</label>
            <div className="relative">
              <input
                type={showPwd ? 'text' : 'password'}
                value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 pr-10 text-sm rounded transition-colors"
                style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}
                placeholder="请输入密码"
              />
              <button type="button" onClick={() => setShowPwd(!showPwd)}
                      className="absolute right-3 top-1/2 -translate-y-1/2"
                      style={{ color: 'var(--text-secondary)' }}>
                {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>
          {error && <p className="text-xs" style={{ color: 'var(--accent-danger)' }}>{error}</p>}
          <button
            type="submit"
            className="w-full py-2.5 text-sm font-semibold rounded mt-2 transition-all hover:shadow-[var(--glow-accent)]"
            style={{ background: 'var(--accent-primary)', color: '#0A0E14' }}
          >
            登 录
          </button>
        </form>
      </div>
    </div>
  );
}
