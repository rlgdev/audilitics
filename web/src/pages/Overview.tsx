// Overview (spec 7.1 #/): reads only latest.json and trends.json (spec 12.1).
// The KPI row and the two trend charts show totals, or one segment's series when exactly one segment is selected;
// they are never recombined from finer groups (spec 7.2).
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { TrendChart } from '../charts/TrendChart';
import { useLatestState } from '../app/latest';
import { EmptyState, ErrorState, ShowData, SimpleTable } from '../components/common';
import { FilterRow } from '../components/FilterRow';
import { FreshnessBar, HotConfigCard, KpiTile, ModelTile } from '../components/tiles';
import { useData } from '../lib/data';
import { filterConfigs, periodSlice, useUrlState } from '../lib/filters';
import { fmtDate, fmtInt, fmtPLN, fmtPct, fmtRange } from '../lib/format';
import type { SeriesSet, Trends } from '../lib/types';

function lastOf<T>(a: T[] | undefined): T | null {
  return a && a.length ? a[a.length - 1] : null;
}

export function Overview() {
  const { data: latest, error } = useLatestState();
  const trends = useData<Trends>('dashboard/trends.json');
  const { filters: f, clear } = useUrlState();

  const tiles = useMemo(() => (latest?.models ?? []).filter((m) =>
    (f.retired || m.status === 'active' || f.models.includes(m.slug))
    && (!f.segment || m.segment === f.segment) && (!f.models.length || f.models.includes(m.slug))), [latest, f]);

  if (error) return <ErrorState error={error} retry={() => location.reload()} />;
  if (!latest) return <div className="page loading" aria-busy="true"><p className="muted">Loading…</p></div>;
  if (!latest.run.data_date) return <EmptyState>No run has been collected yet. The collector runs every Monday.</EmptyState>;

  const t = trends.data;
  const set: SeriesSet | null = t ? (f.segment ? t.segments[f.segment] : t.totals) : null;
  const scope = f.segment ? `segment ${f.segment}` : 'all models';
  const [i0, i1] = t ? periodSlice(t.dates, f.period) : [0, 0];
  const dates = t ? t.dates.slice(i0, i1) : [];
  const sl = <T,>(a: T[] | undefined) => (a ?? []).slice(i0, i1);
  const offers = set?.offers ?? [];
  const delta = offers.length > 1 ? offers[offers.length - 1] - offers[offers.length - 2] : null;
  const kp = latest.kpis;
  const ratesNow = set ? Object.entries(set.rates).map(([plan, r]) => ({ plan, v: lastOf(r.rate_min) }))
    .filter((x) => x.v != null).sort((a, b) => (a.v as number) - (b.v as number))[0] : undefined;
  const hot = filterConfigs(latest.hot_configs, { ...f, plans: [], period: 'all' });
  const ch = latest.changes;
  const retiredHidden = latest.models.filter((m) => m.status === 'retired').length;
  const net = (k: 'net_added' | 'net_removed') => lastOf(set?.[k]);

  return (
    <div className={`page${trends.loading ? ' loading' : ''}`}>
      <div className="page-head">
        <h1>Audi stock ready for pickup: price trends</h1>
        <FreshnessBar latest={latest} />
        <FilterRow />
      </div>

      <section aria-label="Key figures" className="kpis">
        <KpiTile label={f.segment ? `Offers in stock, ${scope}` : 'Offers in stock'} value={fmtInt(lastOf(offers))}
          delta={delta} deltaFormat={fmtInt} spark={offers} />
        <KpiTile label="Models with offers" value={fmtInt(f.segment ? tiles.filter((m) => m.offers > 0).length : kp.models.value)}
          delta={f.segment ? null : kp.models.delta} deltaFormat={fmtInt} />
        <KpiTile label="Median discount" value={fmtPct(lastOf(set?.discount_pct_median))} sub="catalog vs special price" />
        <KpiTile label="Lowest monthly rate" value={fmtPLN(f.segment ? ratesNow?.v ?? null : kp.rate_min.rate_min)}
          sub={!f.segment && kp.rate_min.model ? `${kp.rate_min.model.replace(/^Audi /, '')}, ${kp.rate_min.plan_code}, net`
            : ratesNow ? `${ratesNow.plan}, net` : 'Audi Perfect Lease, net'} />
        <KpiTile label="Configurations with a price drop" value={kp.config_drops.first_run ? '–' : fmtInt(f.segment ? lastOf(set?.config_drops ?? []) ?? kp.config_drops.value : kp.config_drops.value)}
          sub={kp.config_drops.first_run ? 'after the second run' : `median price fell since ${fmtDate(ch.previous)}`} />
      </section>

      <section className="section" aria-labelledby="hot-title">
        <div className="section-head">
          <h2 id="hot-title">Hot deals of the last month</h2>
          <span className="ink2 small">{fmtRange(latest.hot_window[0], latest.hot_window[1])}, by configuration</span>
          <span className="spacer" />
          {latest.hot_count > 0 && <Link to="/deals?hot=1">See all ({fmtInt(latest.hot_count)})</Link>}
        </div>
        {latest.hot_count === 0 ? (
          <EmptyState>Hot deals appear after the second collection run.</EmptyState>
        ) : hot.length === 0 ? (
          <EmptyState action={<button className="btn" onClick={clear}>Clear filters</button>}>No hot deals match these filters.</EmptyState>
        ) : (
          <div className="hot-row">{hot.slice(0, 8).map((h) => <HotConfigCard key={h.config_key} deal={h} />)}</div>
        )}
      </section>

      <section className="grid-2" aria-label="Trends">
        <div className="card chart-card">
          <span className="chart-title">Offers in stock</span>
          <span className="chart-sub">{scope}, at each collection run</span>
          {t ? <TrendChart dates={dates} series={[{ name: 'Offers in stock', data: sl(offers), slot: 1 }]} format={fmtInt} axisFormat={(v) => fmtInt(v)} yMin={0} label="Offers in stock over time" />
            : <div className="chart" />}
          <ShowData><SimpleTable headers={['Date', 'Offers']} rows={dates.map((d, i) => [fmtDate(d), fmtInt(sl(offers)[i])])} numeric={[1]} /></ShowData>
        </div>
        <div className="card chart-card">
          <span className="chart-title">Median special price</span>
          <span className="chart-sub">{scope}, PLN gross</span>
          {t ? <TrendChart dates={dates} series={[{ name: 'Median special price', data: sl(set?.special_median), slot: 1 }]} format={fmtPLN} label="Median special price over time" />
            : <div className="chart" />}
          <ShowData><SimpleTable headers={['Date', 'Median special price']} rows={dates.map((d, i) => [fmtDate(d), fmtPLN(sl(set?.special_median)[i])])} numeric={[1]} /></ShowData>
        </div>
      </section>

      <section className="section" aria-labelledby="board-title">
        <div className="section-head">
          <h2 id="board-title">Models</h2>
          <span className="ink2 small">{tiles.length} models in the order the site lists them{!f.retired && retiredHidden ? `; ${retiredHidden} retired hidden` : ''}</span>
        </div>
        {tiles.length ? (
          <div className="board">{tiles.map((m, i) => <ModelTile key={m.slug} tile={m} index={i} />)}</div>
        ) : (
          <EmptyState action={<button className="btn" onClick={clear}>Clear filters</button>}>No models match these filters.</EmptyState>
        )}
      </section>

      <section className="card section" aria-labelledby="changed-title">
        <div className="section-head">
          <h2 id="changed-title">What changed this run</h2>
          <span className="spacer" />
          <Link to="/changes">Open Changes</Link>
        </div>
        {ch.summary.first_run ? (
          <p className="ink2">This is the first collection run ({fmtDate(ch.date)}); changes appear after the next one.</p>
        ) : (
          <div className="grid-3">
            <div className="kpi"><span className="label">Offers added (net, by configuration)</span><span className="value">{fmtInt(net('net_added'))}</span></div>
            <div className="kpi"><span className="label">Offers removed (net, by configuration)</span><span className="value">{fmtInt(net('net_removed'))}</span></div>
            <div className="kpi"><span className="label">Configurations with a price drop</span><span className="value">{fmtInt(ch.summary.price_drops)}</span>
              {ch.summary.median_drop_pct != null && <span className="sub">median drop {fmtPct(ch.summary.median_drop_pct)}</span>}</div>
          </div>
        )}
        {(ch.models_new.length > 0 || ch.models_retired.length > 0 || ch.models_returned.length > 0) && (
          <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
            {ch.models_new.map((m) => <li key={`n${m.slug}`}>New model: <Link to={`/model/${m.slug}`}>{m.model}</Link> ({m.cars_now} {m.cars_now === 1 ? 'offer' : 'offers'}){m.possible_rename_of ? `, possibly renamed from ${m.possible_rename_of}` : ''}</li>)}
            {ch.models_retired.map((m) => <li key={`r${m.slug}`}>Retired: <Link to={`/model/${m.slug}`}>{m.model}</Link> (no offers for three runs)</li>)}
            {ch.models_returned.map((m) => <li key={`b${m.slug}`}>Back in stock: <Link to={`/model/${m.slug}`}>{m.model}</Link></li>)}
          </ul>
        )}
      </section>
    </div>
  );
}
