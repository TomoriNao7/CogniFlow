import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Plus, Play, Pause, Settings, MoreHorizontal } from 'lucide-react';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import Table from '../components/ui/Table';
import Modal from '../components/ui/Modal';
import Input from '../components/ui/Input';
import Select from '../components/ui/Select';
import DropdownMenu from '../components/ui/DropdownMenu';
import { showToast } from '../components/ui/Toast';

/* ---- Zod Schema ---- */
const toolSchema = z.object({
  name: z.string().min(1, '请输入工具标识').regex(/^[a-z_][a-z0-9_]*$/, '仅限小写字母、数字和下划线'),
  displayName: z.string().min(1, '请输入显示名称'),
  description: z.string().min(1, '请输入工具描述'),
  httpMethod: z.enum(['POST', 'GET', 'PUT', 'DELETE']),
  endpointUrl: z.string().url('请输入有效的 URL'),
  timeoutMs: z.string().regex(/^\d+$/, '请输入数字').transform(Number).pipe(z.number().min(500).max(30000)),
  retryCount: z.string().regex(/^\d+$/, '请输入数字').transform(Number).pipe(z.number().min(0).max(5)),
  version: z.string().min(1, '请输入版本号'),
});

type ToolFormData = z.infer<typeof toolSchema>;

/* ---- 组件 ---- */
interface ToolRow { id: number; name: string; displayName: string; httpMethod: string; version: string; status: string; }

const MOCK: ToolRow[] = [
  { id: 1, name: 'query_order', displayName: '查订单', httpMethod: 'POST', version: '1.0', status: 'active' },
  { id: 2, name: 'check_logistics', displayName: '查物流', httpMethod: 'POST', version: '1.0', status: 'active' },
  { id: 3, name: 'initiate_refund', displayName: '发起退款', httpMethod: 'POST', version: '1.0', status: 'active' },
];

const METHOD_COLORS: Record<string, 'accent' | 'success' | 'warning'> = { POST: 'accent', GET: 'success', PUT: 'warning', DELETE: 'danger' };

export default function Tools() {
  const [modalOpen, setModalOpen] = useState(false);

  const {
    register, handleSubmit, reset,
    formState: { errors },
  } = useForm<ToolFormData>({ resolver: zodResolver(toolSchema), defaultValues: { httpMethod: 'POST', timeoutMs: '5000', retryCount: '2', version: '1.0' } });

  const onSubmit = (data: ToolFormData) => {
    console.log('Tool registered:', data);
    showToast('success', `工具「${data.displayName}」注册成功`);
    setModalOpen(false);
    reset();
  };

  const columns = [
    { key: 'displayName', header: '工具名称', render: (r: ToolRow) => <span className="font-medium">{r.displayName}</span> },
    { key: 'name', header: '标识', width: '150px', render: (r: ToolRow) => <code className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>{r.name}</code> },
    { key: 'httpMethod', header: '方法', width: '80px', render: (r: ToolRow) => <Badge variant={METHOD_COLORS[r.httpMethod] || 'default'}>{r.httpMethod}</Badge> },
    { key: 'version', header: '版本', width: '70px', render: (r: ToolRow) => <span className="font-mono text-sm">{r.version}</span> },
    { key: 'status', header: '状态', width: '80px', render: (r: ToolRow) => r.status === 'active' ? <Badge variant="success">启用</Badge> : <Badge variant="default">停用</Badge> },
    { key: 'actions', header: '操作', width: '60px', render: () => (
      <DropdownMenu
        trigger={<MoreHorizontal size={16} color="var(--text-secondary)" />}
        items={[
          { label: '测试', icon: <Play size={14} />, onClick: () => showToast('success', '测试通过') },
          { label: '停用', icon: <Pause size={14} />, onClick: () => showToast('warning', '工具已停用') },
          { label: '配置', icon: <Settings size={14} />, onClick: () => {} },
        ]}
        align="right"
      />
    )},
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>工具管理</h1>
        <Button onClick={() => setModalOpen(true)}><Plus size={16} /> 注册工具</Button>
      </div>
      <Card><Table columns={columns} data={MOCK} /></Card>

      <Modal open={modalOpen} onClose={() => { setModalOpen(false); reset(); }} title="注册新工具" width="640px">
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-4">
            <Input label="工具标识" placeholder="query_order" error={errors.name?.message} {...register('name')} />
            <Input label="显示名称" placeholder="查订单" error={errors.displayName?.message} {...register('displayName')} />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>描述</label>
            <textarea
              {...register('description')}
              className="px-3 py-2 text-sm rounded resize-none h-16"
              style={{ background: 'var(--bg-tertiary)', border: `1px solid ${errors.description ? 'var(--accent-danger)' : 'var(--border-default)'}`, color: 'var(--text-primary)' }}
              placeholder="根据用户手机号查询最近30天订单…"
            />
            {errors.description && <span className="text-xs" style={{ color: 'var(--accent-danger)' }}>{errors.description.message}</span>}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="请求方法" options={[
              { value: 'POST', label: 'POST' }, { value: 'GET', label: 'GET' },
              { value: 'PUT', label: 'PUT' }, { value: 'DELETE', label: 'DELETE' },
            ]} {...register('httpMethod')} />
            <Input label="版本号" placeholder="1.0" error={errors.version?.message} {...register('version')} />
          </div>
          <Input label="接口地址" placeholder="https://api.example.com/orders/query" error={errors.endpointUrl?.message} {...register('endpointUrl')} />
          <div className="grid grid-cols-2 gap-4">
            <Input label="超时时间 (ms)" type="number" placeholder="5000" error={errors.timeoutMs?.message} {...register('timeoutMs')} />
            <Input label="重试次数" type="number" placeholder="2" error={errors.retryCount?.message} {...register('retryCount')} />
          </div>
          <div className="flex justify-end gap-3 mt-4">
            <Button variant="secondary" type="button" onClick={() => { setModalOpen(false); reset(); }}>取消</Button>
            <Button type="submit">注册工具</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
