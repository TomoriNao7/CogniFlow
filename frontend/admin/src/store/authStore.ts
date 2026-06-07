import { create } from 'zustand';
import type { AdminUser } from '../types';

interface AuthState {
  user: AdminUser | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,

  login: async (username: string, _password: string) => {
    /* Mock 登录 —— 后端就绪后替换为真实 API */
    if (!username) return false;
    set({
      isAuthenticated: true,
      token: 'mock-token-' + Date.now(),
      user: { id: 1, username, role: 'admin' },
    });
    return true;
  },

  logout: () => set({ user: null, token: null, isAuthenticated: false }),
}));
