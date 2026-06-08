import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // 明日方舟暗黑主题色
        ark: {
          bg:        'var(--bg-primary)',
          'bg-alt':  'var(--bg-secondary)',
          'bg-card': 'var(--bg-tertiary)',
          'bubble-bot':  'var(--bg-bot-bubble)',
          'bubble-user': 'var(--bg-user-bubble)',
          border:    'var(--border-default)',
          'border-accent': 'var(--border-accent)',
          text:      'var(--text-primary)',
          'text-secondary': 'var(--text-secondary)',
          'text-disabled':  'var(--text-disabled)',
          accent:    'var(--accent-primary)',
          'accent-deep': 'var(--accent-deep)',
          'accent-glow': 'var(--accent-glow)',
          cyan:      'var(--accent-cyan)',
          danger:    'var(--accent-danger)',
          success:   'var(--accent-success)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      fontSize: {
        xs:   ['11px', { lineHeight: '1.5' }],
        sm:   ['13px', { lineHeight: '1.5' }],
        base: ['14px', { lineHeight: '1.6' }],
        lg:   ['16px', { lineHeight: '1.5' }],
        xl:   ['20px', { lineHeight: '1.3' }],
        '2xl': ['24px', { lineHeight: '1.3' }],
      },
      borderRadius: {
        ark: '3px',
      },
      animation: {
        'bubble-in':   'bubble-in 0.25s ease-out',
        breathe:       'breathe 2s ease-in-out infinite',
        blink:         'blink 1s steps(1) infinite',
        'dot-bounce':  'dot-bounce 1.4s infinite ease-in-out both',
      },
      keyframes: {
        'bubble-in': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        breathe: {
          '0%, 100%': { opacity: '1',   boxShadow: '0 0 4px rgba(208,120,40,0.5)' },
          '50%':      { opacity: '0.6', boxShadow: '0 0 14px rgba(240,160,48,0.7)' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0' },
        },
        'dot-bounce': {
          '0%, 80%, 100%': { transform: 'scale(0)' },
          '40%':           { transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
