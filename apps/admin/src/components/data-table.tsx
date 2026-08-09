import { ChevronLeft, ChevronRight, SlidersHorizontal } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./primitives";
import { StatePanel } from "./feedback";

export interface DataColumn<T> {
  id: string;
  header: string;
  cell: (row: T) => ReactNode;
  numeric?: boolean;
}

interface DataTableProps<T> {
  caption: string;
  columns: DataColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyTitle: string;
  emptyDescription: string;
}

export function DataTable<T>({
  caption,
  columns,
  rows,
  rowKey,
  emptyTitle,
  emptyDescription,
}: DataTableProps<T>): React.ReactNode {
  if (rows.length === 0) {
    return <StatePanel title={emptyTitle} description={emptyDescription} />;
  }
  return (
    <>
      <div className="data-table-wrap">
        <table className="data-table">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column.id}
                  scope="col"
                  className={column.numeric ? "numeric" : undefined}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={rowKey(row)}>
                {columns.map((column) => (
                  <td
                    key={column.id}
                    className={column.numeric ? "numeric" : undefined}
                  >
                    {column.cell(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="data-list" aria-label={`${caption} compact view`}>
        {rows.map((row) => (
          <article key={rowKey(row)}>
            {columns.map((column) => (
              <div key={column.id}>
                <dt>{column.header}</dt>
                <dd>{column.cell(row)}</dd>
              </div>
            ))}
          </article>
        ))}
      </div>
    </>
  );
}

export function FilterBar({
  children,
  onOpenFilters,
}: {
  children?: ReactNode;
  onOpenFilters: () => void;
}): React.ReactNode {
  return (
    <div className="filter-bar" role="search">
      <div>{children}</div>
      <Button
        variant="secondary"
        icon={<SlidersHorizontal size={18} />}
        onClick={onOpenFilters}
      >
        Filters
      </Button>
    </div>
  );
}

export function Pagination({
  page,
  pageCount,
  onPageChange,
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}): React.ReactNode {
  return (
    <nav className="pagination" aria-label="Pagination">
      <Button
        variant="ghost"
        icon={<ChevronLeft size={18} />}
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        Previous
      </Button>
      <span aria-live="polite">
        Page {page} of {Math.max(pageCount, 1)}
      </span>
      <Button
        variant="ghost"
        icon={<ChevronRight size={18} />}
        disabled={page >= pageCount}
        onClick={() => onPageChange(page + 1)}
      >
        Next
      </Button>
    </nav>
  );
}
