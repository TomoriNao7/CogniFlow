export default function QuickReply({ onSend }: { onSend: (text: string) => void }) {
  const items = [
    '📱 iPhone 15 Pro 什么颜色？',
    '🎫 现在有什么优惠活动？',
    '💳 支付失败了怎么办？',
    '📮 怎么修改收货地址？',
    '🧾 如何申请发票？',
    '👑 PLUS 会员有什么权益？',
  ];

  return (
    <div
      className="flex gap-2 px-3 py-2 overflow-x-auto"
      style={{
        background: 'var(--bg-primary)',
        borderTop: '1px solid var(--border-default)',
      }}
    >
      {items.map((label) => (
        <button
          key={label}
          onClick={() => onSend(label)}
          className="flex-shrink-0 px-3 py-1.5 text-xs tracking-wide transition-all duration-150"
          style={{
            background: 'var(--bg-tertiary)',
            color: 'var(--text-secondary)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-sm)',
            fontFamily: "'JetBrains Mono', monospace",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--accent-primary)';
            e.currentTarget.style.color = '#1A1A28';
            e.currentTarget.style.borderColor = 'var(--accent-primary)';
            e.currentTarget.style.boxShadow = 'var(--glow-accent)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--bg-tertiary)';
            e.currentTarget.style.color = 'var(--text-secondary)';
            e.currentTarget.style.borderColor = 'var(--border-default)';
            e.currentTarget.style.boxShadow = 'none';
          }}
        >
          &gt; {label}
        </button>
      ))}
    </div>
  );
}
