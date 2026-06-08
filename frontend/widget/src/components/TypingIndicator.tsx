export default function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div
        className="flex items-center gap-2 px-4 py-3 max-w-[80%] animate-bubble-in"
        style={{
          background: 'var(--bg-bot-bubble)',
          borderRadius: 'var(--radius-sm) var(--radius-lg) var(--radius-lg) var(--radius-lg)',
          border: '1px solid var(--border-default)',
        }}
      >
        <span
          className="text-xs tracking-wider"
          style={{
            color: 'var(--text-secondary)',
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          处理中
        </span>
        <span className="w-1.5 h-1.5 dot-bounce" style={{ background: 'var(--accent-primary)', borderRadius: '50%' }} />
        <span className="w-1.5 h-1.5 dot-bounce" style={{ background: 'var(--accent-primary)', borderRadius: '50%' }} />
        <span className="w-1.5 h-1.5 dot-bounce" style={{ background: 'var(--accent-primary)', borderRadius: '50%' }} />
      </div>
    </div>
  );
}
