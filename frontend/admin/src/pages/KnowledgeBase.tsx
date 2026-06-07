import { useState } from 'react';
import { Upload, FileText, MoreHorizontal, Eye, Archive, RotateCcw, Trash2 } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import Badge from '../components/ui/Badge';
import PaginatedTable from '../components/ui/PaginatedTable';
import DropdownMenu from '../components/ui/DropdownMenu';
import { showToast } from '../components/ui/Toast';

interface DocRow { id: number; title: string; fileType: string; splitMethod: string; chunkCount: number; totalRetrievals: number; status: 'active' | 'archived'; createdAt: string; }

const MOCK: DocRow[] = [
  { id: 1, title: '退换货政策', fileType: 'md', splitMethod: 'structure', chunkCount: 24, totalRetrievals: 1203, status: 'active', createdAt: '2024-06-01' },
  { id: 2, title: '常见问题 FAQ', fileType: 'faq', splitMethod: 'qa_boundary', chunkCount: 56, totalRetrievals: 3401, status: 'active', createdAt: '2024-05-28' },
  { id: 3, title: '物流说明文档', fileType: 'pdf', splitMethod: 'semantic', chunkCount: 18, totalRetrievals: 890, status: 'active', createdAt: '2024-06-03' },
  { id: 4, title: '新品上市公告', fileType: 'txt', splitMethod: 'fixed_size', chunkCount: 12, totalRetrievals: 430, status: 'active', createdAt: '2024-06-05' },
  { id: 5, title: '支付方式说明', fileType: 'md', splitMethod: 'structure', chunkCount: 8, totalRetrievals: 2670, status: 'active', createdAt: '2024-05-20' },
  { id: 6, title: '优惠活动规则', fileType: 'md', splitMethod: 'structure', chunkCount: 15, totalRetrievals: 1840, status: 'archived', createdAt: '2024-05-15' },
  { id: 7, title: '会员权益手册', fileType: 'pdf', splitMethod: 'semantic', chunkCount: 30, totalRetrievals: 920, status: 'active', createdAt: '2024-06-02' },
  { id: 8, title: '发票开具说明', fileType: 'faq', splitMethod: 'qa_boundary', chunkCount: 22, totalRetrievals: 1560, status: 'active', createdAt: '2024-05-30' },
];

const METHOD_LABEL: Record<string, string> = { structure: '文档结构', semantic: '语义切片', qa_boundary: 'Q&A边界', fixed_size: '固定大小' };

export default function KnowledgeBase() {
  const [search, setSearch] = useState('');
  const [uploadOpen, setUploadOpen] = useState(false);

  const columns = [
    { key: 'title', header: '文档名称', sortable: true, render: (r: DocRow) => (
      <div className="flex items-center gap-2"><FileText size={14} style={{ color: 'var(--text-secondary)' }} />{r.title}</div>
    )},
    { key: 'fileType', header: '格式', width: '80px', render: (r: DocRow) => <Badge variant="default">{r.fileType.toUpperCase()}</Badge> },
    { key: 'splitMethod', header: '切分方式', width: '100px', render: (r: DocRow) => <span style={{ color: 'var(--text-secondary)' }}>{METHOD_LABEL[r.splitMethod] || r.splitMethod}</span> },
    { key: 'chunkCount', header: '切片数', width: '80px', sortable: true, render: (r: DocRow) => <span className="font-mono text-sm">{r.chunkCount}</span> },
    { key: 'totalRetrievals', header: '检索次数', width: '90px', sortable: true, render: (r: DocRow) => <span className="font-mono text-sm">{r.totalRetrievals.toLocaleString()}</span> },
    { key: 'status', header: '状态', width: '80px', render: (r: DocRow) => r.status === 'active' ? <Badge variant="success">启用</Badge> : <Badge variant="default">归档</Badge> },
    { key: 'actions', header: '', width: '50px', render: (r: DocRow) => (
      <DropdownMenu
        trigger={<MoreHorizontal size={16} style={{ color: 'var(--text-secondary)' }} />}
        items={[
          { label: '查看切片', icon: <Eye size={14} />, onClick: () => showToast('success', `查看「${r.title}」切片`), },
          ...(r.status === 'active'
            ? [{ label: '归档', icon: <Archive size={14} />, onClick: () => showToast('warning', `「${r.title}」已归档`) }]
            : [{ label: '重新启用', icon: <RotateCcw size={14} />, onClick: () => showToast('success', `「${r.title}」已启用`) }]
          ),
          { label: '删除', icon: <Trash2 size={14} />, danger: true, onClick: () => showToast('error', `「${r.title}」已删除`) },
        ]}
        align="right"
      />
    )},
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>知识库管理</h1>
        <Button onClick={() => setUploadOpen(true)}><Upload size={16} /> 上传文档</Button>
      </div>

      <div className="flex items-center gap-4">
        <div className="w-72">
          <Input placeholder="搜索文档…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
      </div>

      <Card>
        <PaginatedTable
          columns={columns}
          data={MOCK.filter((d) => d.title.includes(search))}
          pageSize={5}
        />
      </Card>

      {uploadOpen && (
        <div className="card" style={{ padding: '40px', textAlign: 'center' }}>
          <Upload size={48} style={{ color: 'var(--text-disabled)', margin: '0 auto' }} />
          <p className="mt-4 text-sm" style={{ color: 'var(--text-secondary)' }}>拖拽文件到此处，或点击下方按钮选择文件</p>
          <p className="mt-1 text-xs" style={{ color: 'var(--text-disabled)' }}>支持 PDF / Markdown / Word / Excel / FAQ / TXT</p>
          <div className="flex gap-3 justify-center mt-5">
            <Button size="sm">选择文件</Button>
            <Button variant="ghost" size="sm" onClick={() => setUploadOpen(false)}>取消</Button>
          </div>
        </div>
      )}
    </div>
  );
}
