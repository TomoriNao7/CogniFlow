import { useEffect, useState } from 'react';
import { FileText, MoreHorizontal, Eye, Archive, RotateCcw } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import PaginatedTable from '../components/ui/PaginatedTable';
import DropdownMenu from '../components/ui/DropdownMenu';
import { showToast } from '../components/ui/Toast';
import { fetchKnowledge, fetchKnowledgeStats, type DocRow, type KnowledgeStats } from '../api/admin';

const METHOD_LABEL: Record<string, string> = {
  md: '文档结构', faq: 'Q&A边界', txt: '固定大小',
  structure: '文档结构', semantic: '语义切片', qa_boundary: 'Q&A边界', fixed_size: '固定大小',
};

export default function KnowledgeBase() {
  const [rows, setRows] = useState<DocRow[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchKnowledge().then(r => setRows(r.rows)).catch(() => {});
    fetchKnowledgeStats().then(setStats).catch(() => {});
  }, []);

  const filtered = rows.filter(d => d.title.includes(search));

  const columns = [
    { key: 'title', header: '文档名称', sortable: true, render: (r: DocRow) => (
      <div className="flex items-center gap-2"><FileText size={14} style={{ color: 'var(--text-secondary)' }} />{r.title}</div>
    )},
    { key: 'file_type', header: '格式', width: '70px', render: (r: DocRow) => <Badge variant="default">{r.file_type.toUpperCase()}</Badge> },
    { key: 'split_method', header: '切分', width: '90px', render: (r: DocRow) => <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{METHOD_LABEL[r.split_method] || r.split_method}</span> },
    { key: 'chunk_count', header: '切片', width: '60px', sortable: true, render: (r: DocRow) => <span className="font-mono text-sm">{r.chunk_count}</span> },
    { key: 'total_retrievals', header: '检索', width: '80px', sortable: true, render: (r: DocRow) => <span className="font-mono text-sm">{r.total_retrievals}</span> },
    { key: 'status', header: '状态', width: '70px', render: (r: DocRow) =>
      r.status === 'active' ? <Badge variant="success">启用</Badge> : <Badge variant="default">归档</Badge>
    },
    { key: 'actions', header: '', width: '50px', render: (r: DocRow) => (
      <DropdownMenu
        trigger={<MoreHorizontal size={16} style={{ color: 'var(--text-secondary)' }} />}
        items={[
          { label: '查看切片', icon: <Eye size={14} />, onClick: () => showToast('success', `查看「${r.title}」切片`) },
          { label: r.status === 'active' ? '归档' : '启用', icon: r.status === 'active' ? <Archive size={14} /> : <RotateCcw size={14} />, onClick: () => showToast('warning', `「${r.title}」状态已变更`) },
        ]}
        align="right"
      />
    )},
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>知识库管理</h1>
        <div className="flex gap-3 text-xs" style={{ color: 'var(--text-secondary)' }}>
          <span>{stats?.total_documents ?? 0} 篇文档</span>
          <span>{stats?.total_chunks ?? 0} 个切片</span>
          <span>{(stats?.total_retrievals ?? 0).toLocaleString()} 次检索</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <input
          placeholder="搜索文档…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-72 px-3 py-2 text-sm rounded border outline-none"
          style={{ background: 'var(--bg-primary)', borderColor: 'var(--border-default)', color: 'var(--text-primary)' }}
        />
      </div>

      <Card>
        {filtered.length === 0 ? (
          <p className="text-sm py-8 text-center" style={{ color: 'var(--text-disabled)' }}>
            {rows.length === 0 ? '暂无知识文档，请运行 python scripts/ingest.py 注入知识库' : '无匹配文档'}
          </p>
        ) : (
          <PaginatedTable columns={columns} data={filtered} pageSize={10} />
        )}
      </Card>
    </div>
  );
}
