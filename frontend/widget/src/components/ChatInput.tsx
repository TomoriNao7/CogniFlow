import { useState } from 'react';
import { CornerDownRight } from 'lucide-react';

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

  const canSend = !!text.trim() && !disabled;

  return (
    <div
      className="flex items-end gap-2 px-3 py-3"
      style={{
        background: 'var(--bg-secondary)',
        borderTop: '1px solid var(--border-default)',
      }}
    >
      <textarea
        className="flex-1 resize-none px-3 py-2 text-sm outline-none transition-shadow"
        style={{
          background: 'var(--bg-tertiary)',
          color: 'var(--text-primary)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-md)',
          maxHeight: '100px',
          minHeight: '38px',
          boxShadow: canSend ? 'var(--glow-accent)' : 'none',
        }}
        placeholder="> 输入您的问题…"
        rows={1}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />
      <button
        className="flex-shrink-0 w-9 h-9 flex items-center justify-center transition-all duration-150"
        style={{
          background: canSend ? 'var(--accent-primary)' : 'var(--border-default)',
          borderRadius: 'var(--radius-md)',
          color: canSend ? '#1A1A28' : 'var(--text-disabled)',
          cursor: canSend ? 'pointer' : 'not-allowed',
          boxShadow: canSend ? 'var(--glow-accent)' : 'none',
        }}
        onClick={handleSubmit}
        disabled={!canSend}
      >
        <CornerDownRight size={16} />
      </button>
    </div>
  );
}
