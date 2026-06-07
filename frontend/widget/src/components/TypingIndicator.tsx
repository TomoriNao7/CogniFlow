export default function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div
        className="flex items-center gap-1.5 px-3.5 py-3 rounded-lg max-w-[80%] animate-bubble-in"
        style={{
          background: 'var(--bg-bot-bubble)',
          borderRadius: '4px 12px 12px 12px',
        }}
      >
        <span className="w-2 h-2 rounded-full dot-bounce" style={{ background: 'var(--accent-primary)', animation: 'dot-bounce 1.4s infinite ease-in-out both' }} />
        <span className="w-2 h-2 rounded-full dot-bounce" style={{ background: 'var(--accent-primary)', animation: 'dot-bounce 1.4s 0.2s infinite ease-in-out both' }} />
        <span className="w-2 h-2 rounded-full dot-bounce" style={{ background: 'var(--accent-primary)', animation: 'dot-bounce 1.4s 0.4s infinite ease-in-out both' }} />
      </div>
    </div>
  );
}
