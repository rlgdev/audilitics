// Model (spec 7.1 #/model/:slug): one model over time and its configurations now. The private build adds an
// Offers tab with the offer table.
import { lazy, Suspense, useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { PromoMixChart } from '../charts/PromoMixChart';
import { RangeChart } from '../charts/RangeChart';
import { TrendChart } from '../charts/TrendChart';
import { useLatest } from '../app/latest';
import { EmptyState, ErrorState, ShowData, SimpleTable } from '../components/common';
import { DataTable } from '../components/DataTable';
import { FilterRow } from '../components/FilterRow';
import { ConfigDrawer, configColumns } from '../components/tables';
import { useData } from '../lib/data';
import { IS_PRIVATE } from '../lib/edition';
import { PROMO_ORDER, filterConfigs, periodSlice, useUrlState } from '../lib/filters';
import { fmtDate, fmtDec, fmtInt, fmtPLN } from '../lib/format';
import type { ConfigRow, ModelFile } from '../lib/types';

const ModelOffers = IS_PRIVATE ? lazy(() => import('./private/ModelOffers').then((m) => ({ default: m.ModelOffers }))) : null;

export function Model() {
  const { slug = '' } = useParams();
  const latest = useLatest();
  const file = useData<ModelFile>(`models/${slug}.json`);
  const { sp, filters: f, set, clear } = useUrlState();
  const rows = useMemo(() => (file.data?.configurations ?? []).map((c) => c.current).filter((c): c is ConfigRow => !!c), [file.data]);
  const visible = useMemo(() => filterConfigs(rows, { ...f, models: [], segment: null }), [rows, f]);
  const columns = useMemo(() => configColumns(latest), [latest]);
  const tab = IS_PRIVATE && sp.get('tab') === 'offers' ? 'offers' : 'configs';
  const configKey = sp.get('config');

  if (file.error) {
    return (
      <div className="page">
        <h1>Model not found</h1>
        <EmptyState action={<Link className="btn" to="/">Back to the overview</Link>}>There is no model with the address “{slug}”. It may have been renamed.</EmptyState>
        <ErrorState error={file.error} />
      </div>
    );
  }
  const d = file.data;
  if (!d) return <div className="page loading" aria-busy="true"><p className="muted">Loading…</p></div>;

  const m = d.model;
  const tl = d.timeline;
  const [i0, i1] = periodSlice(d.dates, f.period);
  const dates = d.dates.slice(i0, i1);
  const sl = <T,>(a: T[]) => a.slice(i0, i1);
  const last = tl.offers.length - 1;
  const rates = Object.entries(tl.rates).map(([p, r]) => [p, r.rate_min[last], r.rate_median[last]] as const).filter(([, v]) => v != null);
  const engines = Object.entries(d.engines).filter(([g]) => !f.engines.length || f.engines.includes(g));
  const engineSeries = engines.map(([g, e]) => ({ name: g, data: sl(e.special_median), slot: e.slot || 0, muted: !e.slot }));
  const drawerCfg = configKey ? d.configurations.find((c) => c.config_key === configKey) : undefined;

  return (
    <div className={`page${file.loading ? ' loading' : ''}`}>
      <div className="page-head">
        <span className="small"><Link to="/">Overview</Link></span>
        <h1>{m.name}</h1>
        <p className="ink2">
          Segment {m.segment}. {fmtInt(tl.offers[last] ?? 0)} offers on {fmtDate(d.dates[last])}
          {tl.special_min[last] != null ? `, special prices ${fmtPLN(tl.special_min[last])} to ${fmtPLN(tl.special_max[last])}` : ''}
          {rates.length ? `, rates from ${rates.map(([p, v]) => `${fmtPLN(v)} (${p})`).join(', ')} net` : ''}.
          {' '}Engine groups: {m.engine_groups.join(', ') || 'none listed'}.
          {m.status === 'retired' && ` Retired on ${fmtDate(m.retired_on)}: no offers for three runs.`}
          {m.possible_rename_of && ` Possibly a renamed ${m.possible_rename_of}.`}
        </p>
        <FilterRow hide={['segment', 'model']} />
      </div>

      <section className="grid-2" aria-label="Price trends">
        <div className="card chart-card">
          <span className="chart-title">Special price</span>
          <span className="chart-sub">median with the min–max range at each run, PLN gross</span>
          <RangeChart dates={dates} median={sl(tl.special_median)} min={sl(tl.special_min)} max={sl(tl.special_max)} count={sl(tl.offers)} label={`Special price of ${m.name}: median and range`} className="chart tall" />
          <ShowData><SimpleTable headers={['Date', 'Offers', 'Min', 'Median', 'Max']} numeric={[1, 2, 3, 4]}
            rows={dates.map((dt, i) => [fmtDate(dt), fmtInt(sl(tl.offers)[i]), fmtPLN(sl(tl.special_min)[i]), fmtPLN(sl(tl.special_median)[i]), fmtPLN(sl(tl.special_max)[i])])} /></ShowData>
        </div>
        <div className="card chart-card">
          <span className="chart-title">Like-for-like price index</span>
          <span className="chart-sub">first run = 100; median price change of configurations present with {latest?.directory.min_group ?? 3}+ priced offers in two consecutive runs</span>
          <TrendChart dates={dates} series={[{ name: 'Like-for-like index', data: sl(tl.lfl_index ?? []), slot: 1 }]} format={(v) => fmtDec(v)} axisFormat={(v) => fmtDec(v)} label={`Like-for-like price index of ${m.name}`} className="chart tall" />
          <ShowData><SimpleTable headers={['Date', 'Index']} numeric={[1]} rows={dates.map((dt, i) => [fmtDate(dt), fmtDec(sl(tl.lfl_index ?? [])[i])])} /></ShowData>
        </div>
      </section>

      <section className="grid-2" aria-label="Engines and promos">
        <div className="card chart-card">
          <span className="chart-title">Median special price by engine group</span>
          <span className="chart-sub">one line per engine group, fixed colours</span>
          {engineSeries.length ? <TrendChart dates={dates} series={engineSeries} format={fmtPLN} label={`Median special price by engine group of ${m.name}`} />
            : <EmptyState>No engine group matches the filter.</EmptyState>}
          <ShowData><SimpleTable headers={['Date', ...engineSeries.map((s) => s.name)]} numeric={engineSeries.map((_, k) => k + 1)}
            rows={dates.map((dt, i) => [fmtDate(dt), ...engineSeries.map((s) => fmtPLN(s.data[i]))])} /></ShowData>
        </div>
        <div className="card chart-card">
          <span className="chart-title">Promo mix</span>
          <span className="chart-sub">offers per badge at each run; one offer can carry several badges</span>
          {latest && <PromoMixChart dates={dates} counts={Object.fromEntries(Object.entries(tl.promo_counts).map(([k, v]) => [k, sl(v).map((x) => x ?? 0)]))} promos={latest.directory.promos} order={PROMO_ORDER} label={`Promo mix of ${m.name}`} />}
          <ShowData><SimpleTable headers={['Date', ...PROMO_ORDER.map((k) => latest?.directory.promos[k].name ?? k)]} numeric={PROMO_ORDER.map((_, k) => k + 1)}
            rows={dates.map((dt, i) => [fmtDate(dt), ...PROMO_ORDER.map((k) => fmtInt(sl(tl.promo_counts[k] ?? [])[i]))])} /></ShowData>
        </div>
      </section>

      <section className="section" aria-labelledby="configs-title">
        <h2 id="configs-title">{IS_PRIVATE ? 'In stock now' : 'Configurations in stock now'}</h2>
        {IS_PRIVATE && (
          <div className="tabs" role="tablist" aria-label="Table">
            <button role="tab" aria-selected={tab === 'configs'} onClick={() => set({ tab: null })}>Configurations</button>
            <button role="tab" aria-selected={tab === 'offers'} onClick={() => set({ tab: 'offers' })}>Offers</button>
          </div>
        )}
        {tab === 'offers' && ModelOffers ? (
          <Suspense fallback={<p className="muted">Loading…</p>}><ModelOffers slug={slug} /></Suspense>
        ) : rows.length === 0 ? (
          <EmptyState>{m.status === 'retired' ? 'This model has no offers in stock; its history stays above.' : `No configuration has ${latest?.directory.min_group ?? 3} or more priced offers in the latest run.`}</EmptyState>
        ) : visible.length === 0 ? (
          <EmptyState action={<button className="btn" onClick={clear}>Clear filters</button>}>No configurations match these filters.</EmptyState>
        ) : (
          <>
            <p className="small ink2">Configurations with at least {latest?.directory.min_group ?? 3} priced offers: model, engine, model code and model year.</p>
            <DataTable noun={['configuration', 'configurations']} rows={visible} columns={columns} rowKey={(r) => r.config_key} storageKey="configs" csvName={`audilitics-${slug}-configurations.csv`}
              defaultSort={{ id: 'special_median', desc: false }} onRowClick={(r) => set({ config: r.config_key })} caption={`Configurations of ${m.name}`} height={480} />
          </>
        )}
      </section>
      {drawerCfg?.current && (
        <ConfigDrawer row={drawerCfg.current} history={drawerCfg.history} dates={d.dates} onClose={() => set({ config: null })} />
      )}
    </div>
  );
}
