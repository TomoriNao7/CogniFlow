import { useState } from 'react';
import { Send } from 'lucide-react';

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('');

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex items-end gap-2 px-3 py-3 border-t" style={{ borderColor: 'var(--border-default)' }}>
      <textarea
        className="flex-1 resize-none rounded-lg px-3 py-2 text-sm outline-none"
        style={{
          background: 'var(--bg-secondary)',
          color: 'var(--text-primary)',
          maxHeight: '100px',
          minHeight: '40px',
        }}
        placeholder="输入您的问题…"
        rows={1}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />
      <button
        className="flex-shrink-0 w-9 h-9 flex items-center justify-center rounded-lg transition-colors"
        style={{
          background: text.trim() && !disabled ? 'var(--accent-primary)' : '#d0d5dd',
          color: '#fff',
          cursor: text.trim() && !disabled ? 'pointer' : 'not-allowed',
        }}
        onClick={handleSubmit}
        disabled={!text.trim() || disabled}
      >
        <Send size={16} />
      </button>
    </div>
  );
}
