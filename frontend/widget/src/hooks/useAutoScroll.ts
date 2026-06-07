import { useEffect, useRef } from 'react';
import { useChatStore } from '../store/chatStore';

export function useAutoScroll() {
  const bottomRef = useRef<HTMLDivElement>(null);
  const messages = useChatStore((s) => s.messages);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return bottomRef;
}
