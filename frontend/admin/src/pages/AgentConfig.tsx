import { useState } from 'react';
import { Save, RotateCcw } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import Input from '../components/ui/Input';
import Select from '../components/ui/Select';
import { showToast } from '../components/ui/Toast';

const AGENTS = ['pre_sales', 'during_sales', 'after_sales'];
const DISPLAY: Record<string, string> = { pre_sales: '售前客服', during_sales: '售中客服', after_sales: '售后客服' };
const MODELS = [
  { value: 'qwen-max',    label: 'Qwen Max' },
  { value: 'qwen-plus',   label: 'Qwen Plus' },
  { value: 'qwen-turbo',  label: 'Qwen Turbo' },
];

export default function AgentConfig() {
  const [activeAgent, setActiveAgent] = useState('after_sales');
  const [systemPrompt, setSystemPrompt] = useState(
    '你是 CogniFlow 售后客服助手。职责：\n1. 查询物流状态\n2. 处理退款/退货申请\n3. 处理投诉建议\n\n回答要求：简洁、准确、友好。涉及敏感操作时必须引导用户提供必要信息。'
  );
  const [topK, setTopK] = useState('5');
  const [threshold, setThreshold] = useState('0.75');
  const [bm25Weight, setBm25Weight] = useState('0.3');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    showToast('success', `「${DISPLAY[activeAgent]}」配置已保存`);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Agent 配置</h1>

      {/* Agent 选择 */}
      <div className="flex gap-3">
        {AGENTS.map((a) => (
          <button key={a} onClick={() => setActiveAgent(a)}
                  className="px-4 py-2 text-sm font-medium transition-all"
                  style={{
                    color: activeAgent === a ? 'var(--accent-primary)' : 'var(--text-secondary)',
                    borderBottom: activeAgent === a ? '2px solid var(--accent-primary)' : '2px solid transparent',
                  }}>
            {DISPLAY[a]}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Prompt */}
        <Card>
          <h3 className="text-base font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>System Prompt</h3>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            className="w-full h-48 px-3 py-2 text-sm rounded resize-none font-mono"
            style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}
          />
        </Card>

        {/* 检索参数 + 模型 */}
        <div className="flex flex-col gap-6">
          <Card>
            <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>检索参数</h3>
            <div className="grid grid-cols-3 gap-4">
              <Input label="Top K" value={topK} onChange={(e) => setTopK(e.target.value)} />
              <Input label="相似度阈值" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
              <Input label="BM25 权重" value={bm25Weight} onChange={(e) => setBm25Weight(e.target.value)} />
            </div>
          </Card>

          <Card>
            <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>模型配置</h3>
            <Select label="生成模型" options={MODELS} defaultValue="qwen-max" />
            <div className="flex items-center gap-2 mt-3">
              <Badge variant="accent">已绑定 2 个工具</Badge>
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>query_order / check_logistics</span>
            </div>
          </Card>
        </div>
      </div>

      {/* 保存 */}
      <div className="flex gap-3 justify-end">
        <Button variant="secondary"><RotateCcw size={14} /> 重置</Button>
        <Button onClick={handleSave}><Save size={14} /> 保存配置</Button>
      </div>
    </div>
  );
}
