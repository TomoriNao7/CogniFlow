import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        admin: {
          'bg-primary':    'var(--bg-primary)',
          'bg-secondary':  'var(--bg-secondary)',
          'bg-tertiary':   'var(--bg-tertiary)',
          border:          'var(--border-default)',
          'border-light':  'var(--border-light)',
          'border-accent': 'var(--border-accent)',
          accent:          'var(--accent-primary)',
          'accent-deep':   'var(--accent-deep)',
          warning:         'var(--accent-warning)',
          success:         'var(--accent-success)',
          danger:          'var(--accent-danger)',
          'text-primary':  'var(--text-primary)',
          'text-secondary':'var(--text-secondary)',
          'text-disabled': 'var(--text-disabled)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        dropdown: 'var(--shadow-dropdown)',
        glow: 'var(--glow-accent)',
      },
      animation: {
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 4px rgba(0,212,228,0.2)' },
          '50%':      { boxShadow: '0 0 16px rgba(0,212,228,0.4)' },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
