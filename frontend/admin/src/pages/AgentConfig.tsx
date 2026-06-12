import { useEffect, useState } from 'react';
import { Save, RotateCcw } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import Input from '../components/ui/Input';
import Select from '../components/ui/Select';
import { showToast } from '../components/ui/Toast';
import { fetchAgents, updateAgent, type AgentRow } from '../api/admin';

const DISPLAY: Record<string, string> = { pre_sales: '售前客服', during_sales: '售中客服', after_sales: '售后客服' };
const MODELS = [
  { value: 'qwen-max',    label: 'Qwen Max' },
  { value: 'qwen-plus',   label: 'Qwen Plus' },
  { value: 'qwen-turbo',  label: 'Qwen Turbo' },
];

export default function AgentConfig() {
  const [agents, setAgents] = useState<AgentRow[]>([]);
  const [activeName, setActiveName] = useState('after_sales');
  const [model, setModel] = useState('qwen-max');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [topK, setTopK] = useState('5');
  const [threshold, setThreshold] = useState('0.75');
  const [bm25Weight, setBm25Weight] = useState('0.3');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchAgents().then(data => {
      setAgents(data.agents);
      const a = data.agents.find(a => a.name === 'after_sales');
      if (a) loadAgent(a);
    }).catch(() => {});
  }, []);

  const loadAgent = (a: AgentRow) => {
    setActiveName(a.name);
    setModel(a.model);
    setSystemPrompt(a.system_prompt || '');
    setTopK(a.retrieval_params?.top_k || '5');
    setThreshold(a.retrieval_params?.similarity_threshold || '0.75');
    setBm25Weight(a.retrieval_params?.bm25_weight || '0.3');
  };

  const switchAgent = (name: string) => {
    const a = agents.find(x => x.name === name);
    if (a) loadAgent(a);
  };

  const handleSave = async () => {
    const a = agents.find(x => x.name === activeName);
    if (!a) return;
    setSaving(true);
    try {
      await updateAgent(a.id, {
        model, system_prompt: systemPrompt,
        top_k: parseInt(topK), similarity_threshold: parseFloat(threshold), bm25_weight: parseFloat(bm25Weight),
      });
      showToast('success', `「${DISPLAY[activeName]}」配置已保存`);
    } catch {
      showToast('error', '保存失败');
    }
    setSaving(false);
  };

  const current = agents.find(a => a.name === activeName);

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Agent 配置</h1>

      <div className="flex gap-3">
        {['pre_sales', 'during_sales', 'after_sales'].map(a => (
          <button key={a} onClick={() => switchAgent(a)}
                  className="px-4 py-2 text-sm font-medium transition-all"
                  style={{
                    color: activeName === a ? 'var(--accent-primary)' : 'var(--text-secondary)',
                    borderBottom: activeName === a ? '2px solid var(--accent-primary)' : '2px solid transparent',
                  }}>
            {DISPLAY[a]}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-base font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>System Prompt</h3>
          <textarea
            value={systemPrompt}
            onChange={e => setSystemPrompt(e.target.value)}
            className="w-full h-48 px-3 py-2 text-sm rounded resize-none font-mono"
            style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-default)', color: 'var(--text-primary)' }}
          />
        </Card>

        <div className="flex flex-col gap-6">
          <Card>
            <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>检索参数</h3>
            <div className="grid grid-cols-3 gap-4">
              <Input label="Top K" value={topK} onChange={e => setTopK(e.target.value)} />
              <Input label="相似度阈值" value={threshold} onChange={e => setThreshold(e.target.value)} />
              <Input label="BM25 权重" value={bm25Weight} onChange={e => setBm25Weight(e.target.value)} />
            </div>
          </Card>

          <Card>
            <h3 className="text-base font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>模型配置</h3>
            <Select label="生成模型" options={MODELS} value={model} onChange={e => setModel(e.target.value)} />
            <div className="flex items-center gap-2 mt-3">
              <Badge variant="accent">状态</Badge>
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                {current?.status === 'active' ? '运行中' : current?.status ?? '-'} — {DISPLAY[activeName] || activeName}
              </span>
            </div>
          </Card>
        </div>
      </div>

      <div className="flex gap-3 justify-end">
        <Button variant="secondary" onClick={() => switchAgent(activeName)}><RotateCcw size={14} /> 重置</Button>
        <Button onClick={handleSave} disabled={saving}><Save size={14} /> {saving ? '保存中…' : '保存配置'}</Button>
      </div>
    </div>
  );
}
