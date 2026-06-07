import { useState, type ReactNode } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface Column<T> {
  key: string;
  header: string;
  width?: string;
  sortable?: boolean;
  render: (row: T) => ReactNode;
}

interface Props<T> {
  columns: Column<T>[];
  data: T[];
  pageSize?: number;
  onRowClick?: (row: T) => void;
  emptyText?: string;
}

export default function PaginatedTable<T extends { id: number | string }>({
  columns, data, pageSize = 10, onRowClick, emptyText = '暂无数据',
}: Props<T>) {
  const [page, setPage] = useState(1);
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const sorted = sortKey
    ? [...data].sort((a, b) => {
        const va = (a as Record<string, unknown>)[sortKey];
        const vb = (b as Record<string, unknown>)[sortKey];
        const cmp = String(va).localeCompare(String(vb), 'zh-CN');
        return sortDir === 'asc' ? cmp : -cmp;
      })
    : data;

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const paged = sorted.slice((page - 1) * pageSize, page * pageSize);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  return (
    <div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="table-header">
              {columns.map((col) => (
                <th key={col.key} className="px-4 py-3 text-left font-medium" style={{ width: col.width }}>
                  {col.sortable ? (
                    <button onClick={() => handleSort(col.key)}
                            className="flex items-center gap-1 hover:text-[var(--text-primary)] transition-colors">
                      {col.header}
                      {sortKey === col.key && <span className="text-[10px]">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                    </button>
                  ) : col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paged.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center" style={{ color: 'var(--text-disabled)' }}>
                  {emptyText}
                </td>
              </tr>
            ) : (
              paged.map((row) => (
                <tr key={row.id} className={`table-row ${onRowClick ? 'cursor-pointer' : ''}`}
                    onClick={() => onRowClick?.(row)}>
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3 text-sm" style={{ color: 'var(--text-primary)' }}>
                      {col.render(row)}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* 分页控件 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t" style={{ borderColor: 'var(--border-default)' }}>
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            共 {data.length} 条，第 {page} / {totalPages} 页
          </span>
          <div className="flex items-center gap-1">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)}
                    className="p-1 rounded hover:bg-[var(--bg-tertiary)] disabled:opacity-30 transition-colors"
                    style={{ color: 'var(--text-secondary)' }}>
              <ChevronLeft size={16} />
            </button>
            {Array.from({ length: totalPages }).map((_, i) => (
              <button key={i} onClick={() => setPage(i + 1)}
                      className="w-8 h-8 text-xs rounded transition-colors"
                      style={{
                        color: page === i + 1 ? 'var(--accent-primary)' : 'var(--text-secondary)',
                        background: page === i + 1 ? 'rgba(0,212,228,0.12)' : 'transparent',
                      }}>
                {i + 1}
              </button>
            ))}
            <button disabled={page >= totalPages} onClick={() => setPage(page + 1)}
                    className="p-1 rounded hover:bg-[var(--bg-tertiary)] disabled:opacity-30 transition-colors"
                    style={{ color: 'var(--text-secondary)' }}>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
