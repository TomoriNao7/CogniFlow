import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

/* 作为嵌入 Widget 的全局挂载函数 */
function mountWidget(selector: string) {
  const el = document.querySelector(selector);
  if (!el) { console.warn('CogniFlow: mount target not found:', selector); return; }
  ReactDOM.createRoot(el).render(
    <React.StrictMode><App /></React.StrictMode>
  );
}

/* ---- 自动挂载到 #widget-root（开发模式） ---- */
const rootEl = document.getElementById('widget-root');
if (rootEl) {
  ReactDOM.createRoot(rootEl).render(
    <React.StrictMode><App /></React.StrictMode>
  );
}

/* ---- 导出给外部调用 ---- */
export { mountWidget };
