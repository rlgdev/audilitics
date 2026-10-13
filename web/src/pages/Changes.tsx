// Changes (spec 7.1 #/changes): a run compared with the run before it; summary tiles; tabs: new configurations,
// gone configurations, price drops, price rises, stock by model, promo changes (spec 6.2).
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useLatest } from '../app/latest';
import { EmptyState, ErrorState, PromoChip } from '../components/common';
import { DataTable, type Col } from '../components/DataTable';
import { FilterRow } from '../components/FilterRow';
import { RunPicker } from '../components/tables';
import { useData } from '../lib/data';
import { filterConfigs, useUrlState } from '../lib/filters';
import { fmtDate, fmtInt, fmtPLN, fmtPct } from '../lib/format';
import type { ChangesFile, IndexEntry, PromoKey, Segment } from '../lib/types';

type Tab = 'configs_new' | 'configs_gone' | 'price_drops' | 'price_rises' | 'stock' | 'promo_changes';
const TABS: [Tab, string][] = [['configs_new', 'New configurations'], ['configs_gone', 'Gone configurations'], ['price_drops', 'Price drops'], ['price_rises', 'Price rises'], ['stock', 'Stock by model'], ['promo_changes', 'Promo changes']];
type AnyRow = Record<string, unknown> & { slug: string; model: string };

const REASON: Record<string, string> = {
  new_in_stock: 'new in stock', reached_minimum: 'now has enough priced offers', none_left: 'no offers left', below_minimum: 'too few priced offers now',
};

function columnsFor(tab: Tab): Col<AnyRow>[] {
  const model: Col<AnyRow> = { id: 'model', header: 'Model', get: (r) => r.model, card: true,
    render: (r) => <Link to={`/model/${r.slug}`} onClick={(e) => e.stopPropagation()}>{r.model.replace(/^Audi /, '')}</Link> };
  const cfg: Col<AnyRow>[] = [model,
    { id: 'engine', header: 'Engine', get: (r) => r.engine as string, card: true },
    { id: 'code', header: 'Model code', get: (r) => r.code as string },
    { id: 'model_year', header: 'Model year', get: (r) => r.model_year as string },
    { id: 'offers', header: 'Offers now', get: (r) => r.offers as number, numeric: true }];
  const num = (id: string, header: string, fmt: (n: number | null) => string): Col<AnyRow> =>
    ({ id, header, get: (r) => r[id] as number | null, render: (r) => fmt(r[id] as number | null), numeric: true, card: true });
  switch (tab) {
    case 'configs_new': return [...cfg, num('special_median', 'Median special price', fmtPLN), num('score_best', 'Best score', (v) => (v == null ? '–' : String(v))),
      { id: 'reason', header: 'Why', get: (r) => REASON[r.reason as string] ?? (r.reason as string) }];
    case 'configs_gone': return [...cfg, num('special_median', 'Last median special price', fmtPLN),
      { id: 'reason', header: 'Why', get: (r) => REASON[r.reason as string] ?? (r.reason as string) }];
    case 'price_drops':
    case 'price_rises': return [...cfg, num('old', 'Previous median', fmtPLN), num('new', 'New median', fmtPLN), num('diff', 'Difference', fmtPLN), num('pct', 'Change %', fmtPct),
      ...(tab === 'price_drops' ? [num('consecutive_drops', 'Drops in a row', fmtInt)] : [])];
    case 'stock': return [model, num('offers_before', 'Offers before', fmtInt), num('offers', 'Offers now', fmtInt),
      num('net_added', 'Net added', fmtInt), num('net_removed', 'Net removed', fmtInt)];
    case 'promo_changes': return [model, num('offers', 'Offers now', fmtInt), {
      id: 'promo_changes', header: 'Badge counts (before → now)',
      get: (r) => Object.entries(r.promo_changes as Record<string, { before: number; now: number }>).map(([k, v]) => `${k}: ${v.before} → ${v.now}`).join('; '),
      render: (r) => (
        <span className="chips">{(Object.entries(r.promo_changes as Record<PromoKey, { before: number; now: number }>) as [PromoKey, { before: number; now: number }][]).map(([k, v]) => (
          <span key={k} style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}><PromoChip promo={k} /> <span className="num small">{v.before} → {v.now}</span></span>
        ))}</span>
      ) }];
  }
}

export function Changes() {
  const latest = useLatest();
  const index = useData<IndexEntry[]>('snapshots/index.json');
  const { sp, filters: f, set, clear } = useUrlState();
  const okDates = useMemo(() => (index.data ?? []).filter((e) => e.status === 'ok').map((e) => e.date).sort(), [index.data]);
  const run = sp.get('run') && okDates.includes(sp.get('run')!) ? sp.get('run')! : okDates[okDates.length - 1];
  const file = useData<ChangesFile>(run ? `dashboard/changes/${run}.json` : null);
  const tab = (TABS.find(([t]) => t === sp.get('tab'))?.[0] ?? 'price_drops') as Tab;
  const segOf = useMemo(() => new Map((latest?.models ?? []).map((m) => [m.slug, m.segment as Segment])), [latest]);
  const rows = useMemo<AnyRow[]>(() => {
    const ch = file.data;
    if (!ch) return [];
    const list = ch[tab] as unknown as AnyRow[];
    if (tab === 'stock' || tab === 'promo_changes') {
      return list.filter((r) => (!f.segment || segOf.get(r.slug) === f.segment) && (!f.models.length || f.models.includes(r.slug)));
    }
    return filterConfigs(list as unknown as Parameters<typeof filterConfigs>[0], { ...f, promos: [] }) as unknown as AnyRow[];
  }, [file.data, tab, f, segOf]);
  const columns = useMemo(() => columnsFor(tab), [tab]);
  const err = index.error ?? file.error;
  const ch = file.data;

  return (
    <div className={`page${file.loading ? ' loading' : ''}`}>
      <div className="page-head">
        <h1>Changes</h1>
        <p className="ink2">What changed between a collection run and the run before it, by configuration (model, engine, model code and model year) and by model. Single cars are never followed from one run to the next.</p>
        <FilterRow hide={['period', 'promo']} />
      </div>
      {err ? <ErrorState error={err} /> : okDates.length < 2 ? (
        <EmptyState>Changes appear after the second collection run{okDates[0] ? ` (the first was on ${fmtDate(okDates[0])})` : ''}.</EmptyState>
      ) : (
        <>
          <RunPicker dates={okDates} value={run!} onChange={(d) => set({ run: d === okDates[okDates.length - 1] ? null : d })} />
          {ch && ch.summary.first_run ? <EmptyState>The first run has nothing to compare with. Pick a later run.</EmptyState> : ch && (
            <>
              <section className="kpis" aria-label="Summary">
                {([['configs_new', 'New configurations'], ['configs_gone', 'Gone configurations'], ['price_drops', 'Price drops'], ['price_rises', 'Price rises']] as [keyof typeof ch.summary, string][]).map(([k, l]) => (
                  <div key={k} className="card kpi"><span className="label">{l}</span><span className="value">{fmtInt(ch.summary[k] as number)}</span>
                    {k === 'price_drops' && ch.summary.median_drop_pct != null && <span className="sub">median drop {fmtPct(ch.summary.median_drop_pct)}</span>}</div>
                ))}
                <div className="card kpi"><span className="label">Compared with</span><span className="value" style={{ fontSize: 20 }}>{fmtDate(ch.previous)}</span></div>
              </section>
              {(ch.models_new.length + ch.models_retired.length + ch.models_returned.length > 0) && (
                <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
                  {ch.models_new.map((m) => <li key={`n${m.slug}`}>New model: <Link to={`/model/${m.slug}`}>{m.model}</Link>, segment {m.segment}, {m.cars_now} {m.cars_now === 1 ? 'offer' : 'offers'}{m.possible_rename_of ? `; possibly renamed from ${m.possible_rename_of}` : ''}</li>)}
                  {ch.models_retired.map((m) => <li key={`r${m.slug}`}>Retired: <Link to={`/model/${m.slug}`}>{m.model}</Link>, last seen {fmtDate(m.last_seen)}</li>)}
                  {ch.models_returned.map((m) => <li key={`b${m.slug}`}>Returned: <Link to={`/model/${m.slug}`}>{m.model}</Link></li>)}
                </ul>
              )}
              <div className="tabs" role="tablist" aria-label="Change lists">
                {TABS.map(([t, l]) => (
                  <button key={t} role="tab" aria-selected={tab === t} onClick={() => set({ tab: t === 'price_drops' ? null : t, sort: null })}>
                    {l} ({fmtInt((ch[t] as unknown[]).length)})
                  </button>
                ))}
              </div>
              {rows.length === 0 ? (
                <EmptyState action={<button className="btn" onClick={clear}>Clear filters</button>}>Nothing in this list for the chosen run and filters.</EmptyState>
              ) : (
                <DataTable rows={rows} columns={columns} rowKey={(r) => String(r.config_key ?? r.slug)} storageKey={`changes-${tab}`} csvName={`audilitics-${tab}-${run}.csv`} caption={TABS.find(([t]) => t === tab)![1]} />
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
