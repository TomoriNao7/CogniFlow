import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    lib: {
      entry: 'src/main.tsx',
      name: 'CogniFlowWidget',
      formats: ['iife'],
      fileName: () => 'cogniflow-widget.js',
    },
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        assetFileNames: 'cogniflow-widget.[ext]',
      },
    },
  },
  server: {
    port: 5173,
    open: true,
  },
});
