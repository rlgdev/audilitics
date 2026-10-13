// Best deals (spec 7.1 #/deals): ranked configurations by best score, breakdown popover of the median parts,
// flags, promo chips with counts; "top 3 per model" toggle; segment tabs; hot=1 (spec 6.5).
import { useMemo, useState } from 'react';
import { useLatest } from '../app/latest';
import { EmptyState, ErrorState } from '../components/common';
import { DataTable } from '../components/DataTable';
import { FilterRow } from '../components/FilterRow';
import { ConfigDrawer, configColumns } from '../components/tables';
import { useData } from '../lib/data';
import { SEGMENT_LABEL, SEGMENT_TO_CODE, filterConfigs, useUrlState } from '../lib/filters';
import { fmtRange } from '../lib/format';
import type { ConfigRow, DealsFile, ModelFile, Segment } from '../lib/types';

const SEGS: Segment[] = ['A', 'Q', 'S/RS', 'e-tron'];

export function Deals() {
  const latest = useLatest();
  const deals = useData<DealsFile>('dashboard/deals.json');
  const { sp, filters: f, set, clear } = useUrlState();
  const [drawer, setDrawer] = useState<ConfigRow | null>(null);
  const modelFile = useData<ModelFile>(drawer ? `models/${drawer.slug}.json` : null);
  const hot = sp.get('hot') === '1';
  const top3 = sp.get('top3') === '1';
  const visible = useMemo(() => {
    let r = filterConfigs(deals.data?.configs ?? [], f);
    if (hot) r = r.filter((x) => x.hot).sort((a, b) => (b.hot_score ?? 0) - (a.hot_score ?? 0) || (b.drop ?? 0) - (a.drop ?? 0) || a.label.localeCompare(b.label));
    if (top3) {
      const seen = new Map<string, number>();
      r = r.filter((x) => {
        const n = seen.get(x.slug) ?? 0;
        seen.set(x.slug, n + 1);
        return n < 3;
      });
    }
    return r;
  }, [deals.data, f, hot, top3]);
  const columns = useMemo(() => configColumns(latest, { hot }), [latest, hot]);
  const history = drawer ? modelFile.data?.configurations.find((c) => c.config_key === drawer.config_key)?.history ?? null : null;

  if (deals.error) return <ErrorState error={deals.error} retry={() => location.reload()} />;
  return (
    <div className={`page${deals.loading ? ' loading' : ''}`}>
      <div className="page-head">
        <h1>Best deals</h1>
        <p className="ink2">Configurations ranked by their best deal score (0–100): discount depth, price position within the model and engine, the configuration’s price momentum, rate value and promo bonus. Each configuration has at least {latest?.directory.min_group ?? 3} priced offers. Open a score to see the median of each part.</p>
        <FilterRow hide={['period', 'segment']} />
      </div>
      <div className="tabs" role="tablist" aria-label="Segment">
        {[null, ...SEGS].map((s) => (
          <button key={s ?? 'all'} role="tab" aria-selected={f.segment === s} onClick={() => set({ segment: s ? SEGMENT_TO_CODE[s] : null })}>
            {s ? SEGMENT_LABEL[s] : 'All segments'}
          </button>
        ))}
      </div>
      <div className="filters" style={{ paddingTop: 0 }}>
        <label className="check"><input type="checkbox" checked={top3} onChange={(e) => set({ top3: e.target.checked ? '1' : null })} /> Top 3 per model</label>
        <label className="check"><input type="checkbox" checked={hot} onChange={(e) => set({ hot: e.target.checked ? '1' : null })} /> Hot deals of the last month only
          {deals.data && <span className="ink2">({fmtRange(deals.data.hot_window[0], deals.data.hot_window[1])})</span>}</label>
      </div>
      {!deals.data ? <p className="muted">Loading…</p> : visible.length === 0 ? (
        <EmptyState action={<button className="btn" onClick={() => { clear(); set({ hot: null, top3: null }); }}>Clear filters</button>}>
          {hot && deals.data.configs.every((r) => !r.hot) ? 'Hot deals appear after the second collection run.' : 'No configurations match these filters.'}
        </EmptyState>
      ) : (
        <DataTable noun={['configuration', 'configurations']} rows={visible} columns={columns} rowKey={(r) => r.config_key} storageKey="deals" csvName="audilitics-best-configurations.csv"
          defaultSort={hot ? undefined : { id: 'score_best', desc: true }} onRowClick={setDrawer} caption="Best deals by configuration" height={640} />
      )}
      {drawer && <ConfigDrawer row={drawer} history={history} dates={modelFile.data?.dates ?? []} onClose={() => setDrawer(null)} />}
    </div>
  );
}
