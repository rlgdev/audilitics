import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Delta, EmptyState, ThemeToggle } from './common';
import { DataTable, type Col } from './DataTable';
import { KpiTile, ModelTile, ScoreBreakdown } from './tiles';
import { ThemeProvider } from '../lib/theme';
import type { ModelTile as Tile } from '../lib/types';

function wrap(ui: React.ReactNode) {
  return render(<ThemeProvider><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter></ThemeProvider>);
}

describe.each(['light', 'dark'])('components in %s theme', (theme) => {
  beforeEach(() => document.documentElement.setAttribute('data-theme', theme));

  it('KpiTile shows value and a labelled delta', () => {
    wrap(<KpiTile label="Cars in stock" value="4 768" delta={-12} deltaFormat={(n) => String(n)} />);
    expect(screen.getByText('Cars in stock')).toBeInTheDocument();
    expect(screen.getByText('down')).toBeInTheDocument(); // direction is never colour alone
  });

  it('Delta says "no change" for zero', () => {
    wrap(<Delta value={0} format={String} />);
    expect(screen.getByText('no change')).toBeInTheDocument();
  });

  it('ModelTile renders feed strings as text', () => {
    const tile: Tile = { slug: 'q5', name: 'Audi Q5 <b>x</b>', segment: 'Q', status: 'active', order: 1, offers: 3, delta: 1, priced: 3, special_min: 199120, spark: { special_median: [1, 2], priced: [3, 3] }, promos: [], engine_groups: [], first_seen: '2026-10-13', retired_on: null };
    const { container } = wrap(<ModelTile tile={tile} index={0} />);
    expect(container.querySelector('b')).toBeNull();
    expect(screen.getByText('Q5 <b>x</b>')).toBeInTheDocument();
  });

  it('ScoreBreakdown opens on click and shows the formula', () => {
    wrap(<ScoreBreakdown score={71} components={{ D: 80, P: 60, M: 50, R: 70, B: 6 }} />);
    fireEvent.click(screen.getByRole('button', { name: /Deal score 71/ }));
    expect(screen.getByRole('dialog')).toHaveTextContent('0.35 D + 0.25 P + 0.20 M + 0.10 R + B = 71');
  });

  it('ThemeToggle marks the pressed option', () => {
    wrap(<ThemeToggle />);
    fireEvent.click(screen.getByRole('button', { name: 'Dark' }));
    expect(screen.getByRole('button', { name: 'Dark' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('EmptyState carries its action', () => {
    wrap(<EmptyState action={<button>Clear filters</button>}>No cars match these filters.</EmptyState>);
    expect(screen.getByRole('status')).toHaveTextContent('No cars match these filters.');
  });

  it('DataTable renders headers and the row count', () => {
    const cols: Col<{ id: string; v: number }>[] = [{ id: 'id', header: 'Id', get: (r) => r.id }, { id: 'v', header: 'Value', get: (r) => r.v, numeric: true }];
    wrap(<DataTable rows={[{ id: 'a', v: 2 }, { id: 'b', v: 1 }]} columns={cols} rowKey={(r) => r.id} storageKey="t" csvName="t.csv" caption="test" />);
    expect(screen.getByRole('button', { name: /Value/ })).toBeInTheDocument();
    expect(screen.getByText('2 rows')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Export CSV' })).toBeInTheDocument();
  });
});

describe('configuration score breakdown', () => {
  it('shows median parts and says they do not add up', () => {
    wrap(<ScoreBreakdown score={88} components={{ D: 80, P: 60, M: 50, R: 70, B: 6 }} best={88} median={74.5} />);
    fireEvent.click(screen.getByRole('button', { name: /Best score 88/ }));
    expect(screen.getByRole('dialog')).toHaveTextContent('do not add up');
  });
});
