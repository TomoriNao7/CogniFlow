interface Props {
  onSend: (text: string) => void;
}

const QUICK_REPLIES = ['查订单', '查物流', '申请退款', '商品咨询', '优惠活动'];

export default function QuickReply({ onSend }: Props) {
  return (
    <div className="flex gap-2 px-3 py-2 overflow-x-auto border-t" style={{ borderColor: 'var(--border-default)' }}>
      {QUICK_REPLIES.map((label) => (
        <button
          key={label}
          onClick={() => onSend(label)}
          className="flex-shrink-0 px-3 py-1.5 text-xs rounded-full border transition-colors hover:bg-[var(--accent-primary)] hover:text-white hover:border-[var(--accent-primary)]"
          style={{
            background: 'var(--bg-secondary)',
            color: 'var(--text-secondary)',
            borderColor: 'var(--border-default)',
          }}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
