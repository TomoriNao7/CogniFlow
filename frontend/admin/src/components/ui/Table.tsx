import type { ReactNode } from 'react';

interface Column<T> {
  key: string;
  header: string;
  width?: string;
  render: (row: T) => ReactNode;
}

interface Props<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  emptyText?: string;
}

export default function Table<T extends { id: number | string }>({
  columns, data, onRowClick, emptyText = '暂无数据',
}: Props<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="table-header">
            {columns.map((col) => (
              <th key={col.key} className="px-4 py-3 text-left font-medium"
                  style={{ width: col.width }}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center"
                  style={{ color: 'var(--text-disabled)' }}>
                {emptyText}
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr key={row.id} className={`table-row ${onRowClick ? 'cursor-pointer' : ''}`}
                  onClick={() => onRowClick?.(row)}>
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3 text-sm"
                      style={{ color: 'var(--text-primary)' }}>
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
