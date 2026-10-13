// Dealers (spec 7.1 #/dealers, private build only): dealer x offers x median discount, plus small multiples of
// offers per dealer over time. Dealer names never appear in the public build.
import { useMemo } from 'react';
import { Sparkline } from '../../charts/Sparkline';
import { useLatest } from '../../app/latest';
import { EmptyState, ErrorState } from '../../components/common';
import { DataTable, type Col } from '../../components/DataTable';
import { FilterRow } from '../../components/FilterRow';
import { useData } from '../../lib/data';
import { periodSlice, useUrlState } from '../../lib/filters';
import { fmtDate, fmtInt, fmtPct } from '../../lib/format';
import type { DealerSeries, PrivateDealers } from '../../lib/types';

interface Row extends DealerSeries { now: number; disc: number | null; modelsShown: number }

export function Dealers() {
  const latest = useLatest();
  const file = useData<PrivateDealers>('dealers.json', 'private');
  const { filters: f } = useUrlState();
  const scoped = !!(f.segment || f.models.length);
  const rows = useMemo<Row[]>(() => {
    if (!file.data) return [];
    const slugs = new Set((latest?.models ?? []).filter((m) => (!f.segment || m.segment === f.segment) && (!f.models.length || f.models.includes(m.slug))).map((m) => m.slug));
    return file.data.dealers.filter((d) => !f.dealers.length || f.dealers.includes(d.nr)).map((d) => ({
      ...d,
      now: scoped ? Object.entries(d.models_now).filter(([s]) => slugs.has(s)).reduce((a, [, n]) => a + n, 0) : d.offers[d.offers.length - 1] ?? 0,
      disc: d.discount_pct_median[d.discount_pct_median.length - 1] ?? null,
      modelsShown: Object.keys(d.models_now).length,
    })).filter((d) => d.now > 0 || !scoped);
  }, [file.data, f, latest, scoped]);
  const columns = useMemo<Col<Row>[]>(() => [
    { id: 'name', header: 'Dealer', get: (r) => r.name ?? r.nr, card: true },
    { id: 'now', header: scoped ? 'Offers (filtered)' : 'Offers', get: (r) => r.now, render: (r) => fmtInt(r.now), numeric: true, card: true },
    { id: 'disc', header: 'Median discount', get: (r) => r.disc, render: (r) => fmtPct(r.disc), numeric: true, card: true },
    { id: 'models', header: 'Models', get: (r) => r.modelsShown, numeric: true },
    { id: 'city', header: 'City', get: (r) => r.city },
    { id: 'nr', header: 'Dealer number', get: (r) => r.nr, hidden: true },
  ], [scoped]);
  if (file.error) return <ErrorState error={file.error} />;
  const dates = file.data?.dates ?? [];
  const [i0, i1] = periodSlice(dates, f.period);
  return (
    <div className={`page${file.loading ? ' loading' : ''}`}>
      <div className="page-head">
        <h1>Dealers</h1>
        <p className="ink2">Private build: who holds the stock and who discounts most.</p>
        <FilterRow hide={['engine', 'promo', 'plan']} />
      </div>
      {!file.data ? <p className="muted">Loading…</p> : rows.length === 0 ? <EmptyState>No dealers match these filters.</EmptyState> : (
        <>
          <DataTable noun={['dealer', 'dealers']} rows={rows} columns={columns} rowKey={(r) => r.nr} storageKey="dealers" csvName="audilitics-dealers.csv"
            defaultSort={{ id: 'now', desc: true }} caption="Dealers" height={520} />
          <section className="section" aria-labelledby="sm-title">
            <h2 id="sm-title">Offers per dealer over time</h2>
            <p className="small ink2">{dates.length > 1 ? `${fmtDate(dates[i0])} to ${fmtDate(dates[i1 - 1])}` : 'One run so far.'}</p>
            <div className="small-multiples">
              {[...rows].sort((a, b) => b.now - a.now).map((d) => (
                <div key={d.nr} className="card" style={{ display: 'grid', gap: 4 }}>
                  <span className="small" style={{ fontWeight: 600 }}>{d.name}</span>
                  <span className="xs ink2">{fmtInt(d.offers[d.offers.length - 1])} offers now</span>
                  <Sparkline data={d.offers.slice(i0, i1)} slot={1} height={40} label={`Offers at ${d.name} over time`} />
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
