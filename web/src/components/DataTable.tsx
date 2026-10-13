// DataTable (spec 7.3, 7.4): TanStack Table wrapper with sorting (kept in the URL), column chooser
// (kept in localStorage), sticky header, virtualised rows, CSV export of the current view, card rows on phones.
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  getCoreRowModel, getSortedRowModel, useReactTable, type ColumnDef, type SortingState, type VisibilityState,
} from '@tanstack/react-table';
import { useVirtualizer } from '@tanstack/react-virtual';
import { downloadCsv, toCsv } from '../lib/csv';
import { useUrlState } from '../lib/filters';
import { useMediaQuery } from '../lib/theme';

export type Raw = string | number | boolean | null | undefined;

export interface Col<T> {
  id: string;
  header: string;
  get: (r: T) => Raw;            // raw value: sorting and CSV (numbers unformatted)
  render?: (r: T) => ReactNode;  // display
  numeric?: boolean;
  hidden?: boolean;              // hidden by default
  card?: boolean;                // shown on phone card rows
}

interface Props<T> {
  rows: T[];
  columns: Col<T>[];
  rowKey: (r: T) => string;
  storageKey: string;
  sortParam?: string;
  defaultSort?: { id: string; desc: boolean };
  onRowClick?: (r: T) => void;
  csvName: string;
  height?: number;
  caption: string;
  tools?: ReactNode;
  noun?: [string, string];
}

function loadVisibility(key: string): VisibilityState | null {
  try {
    const v = localStorage.getItem(`audilitics.cols.${key}`);
    return v ? (JSON.parse(v) as VisibilityState) : null;
  } catch {
    return null;
  }
}

export function DataTable<T>({ rows, columns, rowKey, storageKey, sortParam = 'sort', defaultSort, onRowClick, csvName, height = 560, caption, tools, noun = ['row', 'rows'] }: Props<T>) {
  const { sp, set } = useUrlState();
  const phone = useMediaQuery('(max-width: 640px)');
  const sortRaw = sp.get(sortParam);
  const sorting: SortingState = useMemo(() => {
    if (sortRaw) {
      const [id, dir] = sortRaw.split(':');
      if (columns.some((c) => c.id === id)) return [{ id, desc: dir === 'desc' }];
    }
    return defaultSort ? [defaultSort] : [];
  }, [sortRaw, columns, defaultSort]);

  const [visibility, setVisibility] = useState<VisibilityState>(() => loadVisibility(storageKey)
    ?? Object.fromEntries(columns.filter((c) => c.hidden).map((c) => [c.id, false])));
  useEffect(() => {
    try {
      localStorage.setItem(`audilitics.cols.${storageKey}`, JSON.stringify(visibility));
    } catch {
      /* storage unavailable */
    }
  }, [visibility, storageKey]);

  const defs = useMemo<ColumnDef<T>[]>(() => columns.map((c) => ({
    id: c.id,
    header: c.header,
    accessorFn: (r: T) => c.get(r),
    sortUndefined: 'last',
    sortingFn: (a, b, id) => {
      const x = a.getValue(id) as Raw;
      const y = b.getValue(id) as Raw;
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      if (typeof x === 'number' && typeof y === 'number') return x - y;
      return String(x).localeCompare(String(y), 'pl');
    },
  })), [columns]);

  const table = useReactTable({
    data: rows,
    columns: defs,
    state: { sorting, columnVisibility: visibility },
    onSortingChange: (u) => {
      const next = typeof u === 'function' ? u(sorting) : u;
      const s = next[0];
      set({ [sortParam]: s ? `${s.id}:${s.desc ? 'desc' : 'asc'}` : null }, true);
    },
    onColumnVisibilityChange: setVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getRowId: (r) => rowKey(r),
    sortDescFirst: false,
  });

  const sorted = table.getRowModel().rows;
  const visibleCols = columns.filter((c) => visibility[c.id] !== false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const rowH = phone ? 124 : 36;
  const v = useVirtualizer({ count: sorted.length, getScrollElement: () => scrollRef.current, estimateSize: () => rowH, overscan: 12 });

  const exportCsv = () => {
    const csv = toCsv(visibleCols.map((c) => c.header), sorted.map((r) => visibleCols.map((c) => c.get(r.original))));
    downloadCsv(csvName, csv);
  };

  const items = v.getVirtualItems();
  const padTop = items.length ? items[0].start : 0;
  const padBottom = items.length ? v.getTotalSize() - items[items.length - 1].end : 0;

  return (
    <div className="section">
      <div className="table-tools">
        <span className="small ink2">{sorted.length.toLocaleString('pl-PL')} {sorted.length === 1 ? noun[0] : noun[1]}</span>
        {tools}
        <span className="spacer" />
        <details className="filter">
          <summary>Columns</summary>
          <div className="filter-menu" style={{ right: 0, left: 'auto' }}>
            {columns.map((c) => (
              <label key={c.id}>
                <input type="checkbox" checked={visibility[c.id] !== false}
                  onChange={(e) => setVisibility((s) => ({ ...s, [c.id]: e.target.checked }))} />
                {c.header}
              </label>
            ))}
            <div className="menu-actions"><button className="linkbtn" onClick={() => setVisibility(Object.fromEntries(columns.filter((c) => c.hidden).map((c) => [c.id, false])))}>Reset columns</button></div>
          </div>
        </details>
        <button className="btn" onClick={exportCsv}>Export CSV</button>
      </div>
      <div className="dt" ref={scrollRef} style={{ maxHeight: height }} tabIndex={-1}>
        {phone ? (
          <div className="cards-list" style={{ paddingTop: padTop, paddingBottom: padBottom }} role="list" aria-label={caption}>
            {items.map((it) => {
              const r = sorted[it.index].original;
              const cardCols = visibleCols.filter((c) => c.card);
              return (
                <div key={sorted[it.index].id} className="car-card" role="listitem" tabIndex={0}
                  onClick={() => onRowClick?.(r)} onKeyDown={(e) => e.key === 'Enter' && onRowClick?.(r)}>
                  <div className="top">
                    <span>{cardCols[0] ? (cardCols[0].render?.(r) ?? String(cardCols[0].get(r) ?? '–')) : rowKey(r)}</span>
                    <span>{cardCols[1] ? (cardCols[1].render?.(r) ?? String(cardCols[1].get(r) ?? '–')) : null}</span>
                  </div>
                  {cardCols.slice(2).map((c) => (
                    <div key={c.id} className="small"><span className="ink2">{c.header}: </span>{c.render?.(r) ?? String(c.get(r) ?? '–')}</div>
                  ))}
                </div>
              );
            })}
          </div>
        ) : (
          <table>
            <caption className="sr-only">{caption}</caption>
            <thead>
              <tr>
                {table.getHeaderGroups()[0].headers.map((h) => {
                  const col = columns.find((c) => c.id === h.id)!;
                  const s = h.column.getIsSorted();
                  return (
                    <th key={h.id} className={col.numeric ? 'r' : ''} scope="col" aria-sort={s === 'asc' ? 'ascending' : s === 'desc' ? 'descending' : 'none'}>
                      <button onClick={h.column.getToggleSortingHandler()}>
                        {col.header}
                        <span aria-hidden="true" style={{ width: 10, display: 'inline-block' }}>{s === 'asc' ? '▲' : s === 'desc' ? '▼' : ''}</span>
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {padTop > 0 && <tr aria-hidden="true" style={{ height: padTop }}><td colSpan={visibleCols.length} style={{ padding: 0, border: 0 }} /></tr>}
              {items.map((it) => {
                const row = sorted[it.index];
                const r = row.original;
                return (
                  <tr key={row.id} tabIndex={onRowClick ? 0 : undefined} style={{ height: rowH }}
                    onClick={() => onRowClick?.(r)} onKeyDown={(e) => { if (e.key === 'Enter') onRowClick?.(r); }}>
                    {visibleCols.map((c) => <td key={c.id} className={c.numeric ? 'r' : ''}>{c.render ? c.render(r) : (c.get(r) ?? '–') as ReactNode}</td>)}
                  </tr>
                );
              })}
              {padBottom > 0 && <tr aria-hidden="true" style={{ height: padBottom }}><td colSpan={visibleCols.length} style={{ padding: 0, border: 0 }} /></tr>}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
