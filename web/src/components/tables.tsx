// Configuration table columns (both builds), offer table columns (private build), ConfigDrawer and RunPicker
// (spec 7.3, 7.4). No column links to audi.pl and no offer has an identifier column.
import { useEffect, useRef } from 'react';
import { RangeChart } from '../charts/RangeChart';
import { useLatest } from '../app/latest';
import { badgePromos } from '../lib/filters';
import { fmtDate, fmtDec, fmtInt, fmtPLN, fmtPct } from '../lib/format';
import type { ConfigHistory, ConfigRow, Latest, OfferRow, PromoKey } from '../lib/types';
import { Flags, PromoChips, PromoCountChips, ShowData, SimpleTable } from './common';
import type { Col } from './DataTable';
import { ScoreBreakdown } from './tiles';

function promoText(counts: ConfigRow['promo_counts'], latest: Latest | null): string {
  if (!counts) return '';
  return (Object.entries(counts) as [PromoKey, number][]).filter(([, n]) => n > 0)
    .map(([k, n]) => `${latest?.directory.promos[k].name ?? k} (${n})`).join('; ');
}

export function configColumns(latest: Latest | null, opts: { hot?: boolean } = {}): Col<ConfigRow>[] {
  const cols: Col<ConfigRow>[] = [
    { id: 'model', header: 'Model', get: (r) => r.model, render: (r) => r.model.replace(/^Audi /, ''), card: true },
    { id: 'engine', header: 'Engine', get: (r) => r.engine, card: true },
    { id: 'code', header: 'Model code', get: (r) => r.code },
    { id: 'model_year', header: 'Model year', get: (r) => r.model_year },
    { id: 'offers', header: 'Offers', get: (r) => r.offers, numeric: true, card: true },
    { id: 'catalog_median', header: 'Catalog price (median)', get: (r) => r.catalog_median, render: (r) => fmtPLN(r.catalog_median), numeric: true },
    { id: 'special_min', header: 'Special price from', get: (r) => r.special_min, render: (r) => fmtPLN(r.special_min), numeric: true, card: true },
    { id: 'special_median', header: 'Special price (median)', get: (r) => r.special_median, render: (r) => fmtPLN(r.special_median), numeric: true, card: true },
    { id: 'discount_pct_median', header: 'Discount % (median)', get: (r) => r.discount_pct_median, render: (r) => fmtPct(r.discount_pct_median), numeric: true, card: true },
    { id: 'discount_pct_max', header: 'Discount % (max)', get: (r) => r.discount_pct_max, render: (r) => fmtPct(r.discount_pct_max), numeric: true },
    { id: 'price_30d_median', header: '30-day price (median)', get: (r) => r.price_30d_median, render: (r) => fmtPLN(r.price_30d_median), numeric: true, hidden: true },
    { id: 'promos', header: 'Promos', get: (r) => promoText(r.promo_counts, latest), render: (r) => <PromoCountChips counts={r.promo_counts} max={2} /> },
    { id: 'rate_min', header: 'Rate from (net)', get: (r) => r.rate_min, render: (r) => fmtPLN(r.rate_min), numeric: true },
    { id: 'plan_code', header: 'Plan', get: (r) => r.plan_code },
    { id: 'initial_fee', header: 'Initial fee', get: (r) => r.initial_fee, render: (r) => fmtPLN(r.initial_fee), numeric: true, hidden: true },
    { id: 'term', header: 'Term (months)', get: (r) => r.term, numeric: true, hidden: true },
    { id: 'score_best', header: 'Best score', get: (r) => r.score_best, numeric: true, card: true,
      render: (r) => <ScoreBreakdown score={r.score_best} components={r.components} best={r.score_best} median={r.score_median} /> },
    { id: 'score_median', header: 'Median score', get: (r) => r.score_median, render: (r) => fmtDec(r.score_median), numeric: true },
    { id: 'flags', header: 'Flags', get: (r) => r.flags.join('; '), render: (r) => <Flags flags={r.flags} /> },
    { id: 'engine_group', header: 'Engine group', get: (r) => r.engine_group, hidden: true },
  ];
  if (opts.hot) {
    cols.splice(5, 0, { id: 'drop', header: 'Median drop this month', get: (r) => r.drop, numeric: true,
      render: (r) => (r.drop ? `${fmtPLN(r.drop)} (${fmtPct(r.drop_pct)})` : '–') });
  }
  return cols;
}

export function offerColumns(latest: Latest | null): Col<OfferRow>[] {
  const promoNames = (r: OfferRow) => badgePromos(r.promo_bits, latest).map((k) => latest?.directory.promos[k].name).join('; ');
  return [
    { id: 'score', header: 'Deal score', get: (r) => r.score, numeric: true, card: true,
      render: (r) => <ScoreBreakdown score={r.score} components={r.score == null ? null : { D: r.D, P: r.P, M: r.M, R: r.R, B: r.B }} /> },
    { id: 'model', header: 'Model', get: (r) => r.model, render: (r) => r.model.replace(/^Audi /, ''), card: true },
    { id: 'engine', header: 'Engine', get: (r) => r.engine, card: true },
    { id: 'code', header: 'Model code', get: (r) => r.code },
    { id: 'model_year', header: 'Model year', get: (r) => r.model_year },
    { id: 'catalog', header: 'Catalog price', get: (r) => r.catalog, render: (r) => fmtPLN(r.catalog), numeric: true },
    { id: 'special', header: 'Special price', get: (r) => r.special, render: (r) => fmtPLN(r.special), numeric: true, card: true },
    { id: 'discount', header: 'Discount', get: (r) => r.discount, render: (r) => fmtPLN(r.discount), numeric: true },
    { id: 'discount_pct', header: 'Discount %', get: (r) => r.discount_pct, render: (r) => fmtPct(r.discount_pct), numeric: true, card: true },
    { id: 'price_30d', header: '30-day price', get: (r) => r.price_30d, render: (r) => fmtPLN(r.price_30d), numeric: true },
    { id: 'promos', header: 'Promos', get: promoNames, render: (r) => <PromoChips bits={r.promo_bits} max={2} /> },
    { id: 'rate', header: 'Rate (net)', get: (r) => r.rate, render: (r) => fmtPLN(r.rate), numeric: true, card: true },
    { id: 'plan_code', header: 'Plan', get: (r) => r.plan_code },
    { id: 'initial_fee', header: 'Initial fee', get: (r) => r.initial_fee, render: (r) => fmtPLN(r.initial_fee), numeric: true },
    { id: 'term', header: 'Term (months)', get: (r) => r.term, numeric: true },
    { id: 'rate_total', header: 'Rates over the term', get: (r) => (r.rate != null ? r.rate * r.term : null), render: (r) => fmtPLN(r.rate != null ? r.rate * r.term : null), numeric: true, hidden: true },
    { id: 'identical', header: 'Identical offers', get: (r) => r.identical, numeric: true },
    { id: 'dealer', header: 'Dealer', get: (r) => r.dealer, card: true },
    { id: 'flags', header: 'Flags', get: (r) => r.flags.join('; '), render: (r) => <Flags flags={r.flags} /> },
    { id: 'offer_id', header: 'Offer', get: (r) => r.offer_id, hidden: true },
    { id: 'engine_group', header: 'Engine group', get: (r) => r.engine_group, hidden: true },
  ];
}

export function ConfigDrawer({ row, history, dates, onClose }: { row: ConfigRow; history: ConfigHistory | null; dates: string[]; onClose: () => void }) {
  const latest = useLatest();
  const closeRef = useRef<HTMLButtonElement>(null);
  const opener = useRef<Element | null>(null);
  useEffect(() => {
    opener.current = document.activeElement;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      (opener.current as HTMLElement | null)?.focus?.();
    };
  }, [onClose]);
  const idx = history ? dates.map((_, i) => i).filter((i) => history.special_median[i] != null) : [];
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-labelledby="drawer-title">
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'start' }}>
          <div>
            <h2 id="drawer-title">{row.model}</h2>
            <p className="ink2 small">{row.engine ?? 'Engine not listed'}, code {row.code}, model year {row.model_year}</p>
          </div>
          <button ref={closeRef} className="btn" onClick={onClose}>Close</button>
        </div>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', alignItems: 'baseline' }}>
          <span style={{ fontSize: 28, fontWeight: 600 }}>{fmtPLN(row.special_median)}</span>
          <span className="ink2">median special price of {fmtInt(row.offers)} offers, from {fmtPLN(row.special_min)}</span>
        </div>
        <Flags flags={row.flags} />
        <section className="chart-card">
          <span className="chart-title">Special price at each run where it had at least {latest?.directory.min_group ?? 3} priced offers</span>
          {history && idx.length ? (
            <RangeChart dates={idx.map((i) => dates[i])} median={idx.map((i) => history.special_median[i])}
              min={idx.map((i) => history.special_min[i])} max={idx.map((i) => history.special_max[i])}
              count={idx.map((i) => history.offers[i] ?? 0)} label={`Special price of ${row.label}`} className="chart short" />
          ) : <span className="muted small">No published history yet.</span>}
          {history && idx.length > 0 && (
            <ShowData><SimpleTable headers={['Date', 'Offers', 'Min', 'Median', 'Max']} numeric={[1, 2, 3, 4]}
              rows={idx.map((i) => [fmtDate(dates[i]), fmtInt(history.offers[i]), fmtPLN(history.special_min[i]), fmtPLN(history.special_median[i]), fmtPLN(history.special_max[i])])} /></ShowData>
          )}
        </section>
        <dl className="kv">
          <dt>Badges</dt><dd><PromoCountChips counts={row.promo_counts} /></dd>
          <dt>Discount</dt><dd>median {fmtPct(row.discount_pct_median)}, up to {fmtPct(row.discount_pct_max)}</dd>
          <dt>Rate</dt><dd>from {fmtPLN(row.rate_min)} net per month ({row.plan_code}, {row.term} months, initial fee {fmtPLN(row.initial_fee)} on the median catalog price)</dd>
          <dt>Deal score</dt><dd>best {row.score_best ?? '–'}, median {fmtDec(row.score_median)}; {fmtInt(row.offers_80)} offers score 80 or more</dd>
          <dt>Catalog price</dt><dd>median {fmtPLN(row.catalog_median)}</dd>
        </dl>
      </aside>
    </>
  );
}

export function RunPicker({ dates, value, onChange }: { dates: string[]; value: string; onChange: (d: string) => void }) {
  return (
    <div className="filters" style={{ paddingTop: 0 }}>
      <label className="check">Run
        <select className="filter-select" value={value} onChange={(e) => onChange(e.target.value)}>
          {[...dates].reverse().map((d, i, arr) => (
            <option key={d} value={d}>{fmtDate(d)}{arr[i + 1] ? ` compared with ${fmtDate(arr[i + 1])}` : ' (first run)'}</option>
          ))}
        </select>
      </label>
    </div>
  );
}
