import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Widget 浅色主题
        widget: {
          bg: 'var(--bg-primary)',
          'bubble-bot': 'var(--bg-bot-bubble)',
          'bubble-user': 'var(--bg-user-bubble)',
          border: 'var(--border-default)',
          text: 'var(--text-primary)',
          'text-secondary': 'var(--text-secondary)',
          accent: 'var(--accent-primary)',
          'accent-deep': 'var(--accent-deep)',
          danger: 'var(--accent-danger)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      fontSize: {
        xs: ['12px', { lineHeight: '1.5' }],
        sm: ['13px', { lineHeight: '1.5' }],
        base: ['14px', { lineHeight: '1.6' }],
        lg: ['16px', { lineHeight: '1.5' }],
        xl: ['20px', { lineHeight: '1.3' }],
        '2xl': ['24px', { lineHeight: '1.3' }],
      },
      borderRadius: {
        bubble: '12px',
      },
      animation: {
        'bubble-in': 'bubble-in 0.2s ease-out',
        breathe: 'breathe 2s ease-in-out infinite',
        blink: 'blink 1s steps(1) infinite',
        'dot-bounce': 'dot-bounce 1.4s infinite ease-in-out both',
      },
      keyframes: {
        'bubble-in': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        breathe: {
          '0%, 100%': { opacity: '1', boxShadow: '0 0 4px rgba(0,212,228,0.3)' },
          '50%': { opacity: '0.6', boxShadow: '0 0 12px rgba(0,212,228,0.6)' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0' },
        },
        'dot-bounce': {
          '0%, 80%, 100%': { transform: 'scale(0)' },
          '40%': { transform: 'scale(1)' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
