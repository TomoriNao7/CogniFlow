import { useState, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';

interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/* 通用 HTTP 请求封装，后端就绪后使用 */
export function useApi<T>() {
  const [state, setState] = useState<ApiState<T>>({ data: null, loading: false, error: null });
  const token = useAuthStore((s) => s.token);

  const request = useCallback(async (url: string, options?: RequestInit) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const res = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          ...options?.headers,
        },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const data = (await res.json()) as T;
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : '未知错误';
      setState({ data: null, loading: false, error: message });
      return null;
    }
  }, [token]);

  const get = useCallback((url: string) => request(url), [request]);
  const post = useCallback((url: string, body: unknown) =>
    request(url, { method: 'POST', body: JSON.stringify(body) }), [request]);
  const put = useCallback((url: string, body: unknown) =>
    request(url, { method: 'PUT', body: JSON.stringify(body) }), [request]);
  const del = useCallback((url: string) =>
    request(url, { method: 'DELETE' }), [request]);

  return { ...state, get, post, put, del, request };
}
