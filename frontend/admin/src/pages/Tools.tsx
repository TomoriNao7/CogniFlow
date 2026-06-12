import { useEffect, useState } from 'react';
import { Play, Pause, MoreHorizontal } from 'lucide-react';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Table from '../components/ui/Table';
import DropdownMenu from '../components/ui/DropdownMenu';
import { showToast } from '../components/ui/Toast';
import { fetchAdminTools, type ToolRow } from '../api/admin';

const METHOD_COLORS: Record<string, 'accent' | 'success' | 'warning'> = {
  POST: 'accent', GET: 'success', PUT: 'warning', DELETE: 'danger',
};

export default function Tools() {
  const [rows, setRows] = useState<ToolRow[]>([]);

  useEffect(() => {
    fetchAdminTools().then(r => setRows(r.tools)).catch(() => {});
  }, []);

  const columns = [
    { key: 'display_name', header: '工具', render: (r: ToolRow) => <span className="font-medium">{r.display_name || r.name}</span> },
    { key: 'name', header: '标识', width: '160px', render: (r: ToolRow) => <code className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>{r.name}</code> },
    { key: 'http_method', header: '方法', width: '70px', render: (r: ToolRow) => <Badge variant={METHOD_COLORS[r.http_method] || 'default'}>{r.http_method}</Badge> },
    { key: 'version', header: '版本', width: '60px', render: (r: ToolRow) => <span className="font-mono text-sm">{r.version}</span> },
    { key: 'status', header: '状态', width: '70px', render: (r: ToolRow) =>
      r.status === 'active' ? <Badge variant="success">启用</Badge> : <Badge variant="default">停用</Badge>
    },
    { key: 'actions', header: '', width: '60px', render: (r: ToolRow) => (
      <DropdownMenu
        trigger={<MoreHorizontal size={16} color="var(--text-secondary)" />}
        items={[
          { label: '测试', icon: <Play size={14} />, onClick: () => showToast('success', `测试 ${r.name} 通过`) },
          { label: '停用', icon: <Pause size={14} />, onClick: () => showToast('warning', `${r.name} 已停用`) },
        ]}
        align="right"
      />
    )},
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>工具管理</h1>
        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{rows.length} 个工具已注册</span>
      </div>
      <Card>
        {rows.length === 0 ? (
          <p className="text-sm py-8 text-center" style={{ color: 'var(--text-disabled)' }}>暂无已注册工具。工具由后端 Agent 模块在启动时注册。</p>
        ) : (
          <Table columns={columns} data={rows} />
        )}
      </Card>
    </div>
  );
}
