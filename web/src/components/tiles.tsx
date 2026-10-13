// FreshnessBar, KpiTile, ModelTile, HotConfigCard, ScoreBreakdown (spec 7.4).
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Sparkline } from '../charts/Sparkline';
import { useLatest } from '../app/latest';
import { daysBetween, fmtDate, fmtDec, fmtInt, fmtPLN, fmtPct, todayIso } from '../lib/format';
import type { Components, HotConfig, Latest, ModelTile as Tile, PromoKey } from '../lib/types';
import { Delta, PromoChip } from './common';

export function FreshnessBar({ latest }: { latest: Latest }) {
  const r = latest.run;
  const age = r.data_date ? daysBetween(r.data_date, todayIso()) : null;
  const stale = age != null && age > r.stale_after_days;
  const suspect = r.status === 'suspect';
  const statusColor = r.status === 'ok' ? 'var(--good-icon)' : r.status === 'suspect' ? 'var(--warning)' : 'var(--critical)';
  return (
    <div>
      <div className="fresh" aria-live="polite">
        <span>Data from {fmtDate(r.data_date)}.</span>
        <span>Next run {fmtDate(r.next_run)}.</span>
        <span><span className="status-dot" style={{ background: statusColor }} aria-hidden="true" /> Last run {r.status ?? 'unknown'}{r.date && r.date !== r.data_date ? ` (${fmtDate(r.date)})` : ''}.</span>
      </div>
      {(stale || suspect) && (
        <div className="strip" role="status">
          <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M7 1 L13 12 L1 12 Z" fill="var(--warning)" /><rect x="6.3" y="5" width="1.4" height="4" fill="#0b0b0b" /><rect x="6.3" y="10" width="1.4" height="1.2" fill="#0b0b0b" /></svg>
          {suspect
            ? `The newest run (${fmtDate(r.date)}) looks incomplete and is held back; figures show ${fmtDate(r.data_date)}.`
            : `Data is ${age} days old; the collector should run every 14 days.`}
        </div>
      )}
    </div>
  );
}

export function KpiTile({ label, value, delta, deltaFormat, upIsGood = true, sub, spark }: {
  label: string; value: string; delta?: number | null; deltaFormat?: (n: number) => string; upIsGood?: boolean; sub?: ReactNode; spark?: (number | null)[];
}) {
  return (
    <div className="card kpi">
      <span className="label">{label}</span>
      <span className="value">{value}</span>
      {delta != null && deltaFormat && <Delta value={delta} format={deltaFormat} upIsGood={upIsGood} suffix="vs previous run" />}
      {sub && <span className="sub">{sub}</span>}
      {spark && spark.filter((v) => v != null).length > 1 && <Sparkline data={spark.slice(-12)} slot={1} />}
    </div>
  );
}

export function ModelTile({ tile, index }: { tile: Tile; index: number }) {
  return (
    <Link to={`/model/${tile.slug}`} className={`tile reveal${tile.status === 'retired' ? ' retired' : ''}`} style={{ animationDelay: `${Math.min(index, 40) * 8}ms` }}>
      <span className="name" title={tile.name}>{tile.name.replace(/^Audi /, '')}</span>
      <span className="row">
        <span className="count">{fmtInt(tile.offers)}<span className="sr-only"> offers</span></span>
        <Delta value={tile.delta} format={fmtInt} upIsGood />
      </span>
      <span className="row">
        <span className="price">{tile.status === 'retired' ? `Retired ${fmtDate(tile.retired_on)}`
          : tile.special_min != null ? `from ${fmtPLN(tile.special_min)}` : 'too few priced offers'}</span>
      </span>
      <Sparkline data={tile.spark.special_median} slot={1} label={`Median special price trend of ${tile.name}`} />
      <span className="chips">{tile.promos.map((p) => <PromoChip key={p} promo={p} />)}</span>
    </Link>
  );
}

export function HotConfigCard({ deal }: { deal: HotConfig }) {
  const top = (Object.entries(deal.promo_counts ?? {}) as [PromoKey, number][]).filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1]).slice(0, 2);
  return (
    <article className="hot">
      <Link to={`/model/${deal.slug}?config=${deal.config_key}`} className="stretched model" style={{ color: 'var(--ink)', textDecoration: 'none' }}>
        {deal.model.replace(/^Audi /, '')}
      </Link>
      <span className="engine" title={deal.engine ?? ''}>{deal.engine ?? 'Engine not listed'}, {deal.model_year}</span>
      <span className="xs ink2">{fmtInt(deal.offers)} offers, median</span>
      <span className="price num">{fmtPLN(deal.special_median)}</span>
      {deal.drop > 0 ? (
        <>
          <span className="delta good">
            <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M5 9 L9 2 L1 2 Z" fill="var(--good-icon)" /></svg>
            <span>−{fmtPLN(deal.drop)} ({fmtPct(deal.drop_pct)})</span>
          </span>
          <span className="xs ink2">median cheaper this month</span>
        </>
      ) : (
        <span className="delta flat">{deal.reasons.includes('new_high_score') ? 'New this month, high score' : 'Lowest price seen'}</span>
      )}
      <span className="small ink2">Best score <strong style={{ color: 'var(--ink)' }}>{deal.score_best}</strong></span>
      <span className="chips">{top.map(([p, n]) => <PromoChip key={p} promo={p} count={n} />)}</span>
      <Sparkline data={deal.points.map((p) => p.special_median)} slot={1} label="Median special price inside the window" />
    </article>
  );
}

/** Popover with the score parts. For a configuration it shows the median components next to the best and
 * median score and says that medians do not add up (spec 7.4). */
export function ScoreBreakdown({ score, components, best, median }: {
  score: number | null; components: Components | null; best?: number | null; median?: number | null;
}) {
  const latest = useLatest();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', close);
    };
  }, [open]);
  if (score == null || !components) return <span className="muted">–</span>;
  const config = best !== undefined;
  const w = latest?.directory.scoring.weights ?? { D: 0.35, P: 0.25, M: 0.2, R: 0.1 };
  const parts: [string, number | null, number][] = [
    ['Discount depth D', components.D, w.D], ['Price position P', components.P, w.P], ['Momentum M', components.M, w.M],
    ['Rate value R', components.R, w.R],
  ];
  return (
    <span ref={ref} style={{ position: 'relative', display: 'inline-block' }} onClick={(e) => e.stopPropagation()}>
      <button className="linkbtn" aria-expanded={open} aria-label={`${config ? 'Best score' : 'Deal score'} ${score}, show breakdown`} onClick={() => setOpen((o) => !o)}
        style={{ fontWeight: 600, color: 'var(--ink)' }}>{score}</button>
      {open && (
        <span className="popover" role="dialog" aria-label="Deal score breakdown" style={{ left: 0, top: '100%', display: 'block' }}>
          {config && <span className="small" style={{ display: 'block', marginBottom: 6 }}>Best {best ?? '–'}, median {median != null ? fmtDec(median) : '–'}. Median of each part:</span>}
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <tbody>
              {parts.map(([l, v, wt]) => (
                <tr key={l}><td>{l}</td><td className="num" style={{ textAlign: 'right', paddingLeft: 12 }}>{v == null ? '–' : v.toFixed(1)}</td><td className="num muted" style={{ textAlign: 'right', paddingLeft: 8 }}>× {wt.toFixed(2)}</td></tr>
              ))}
              <tr><td>Promo bonus B</td><td className="num" style={{ textAlign: 'right' }}>{components.B ?? 0}</td><td className="muted" style={{ textAlign: 'right' }}>+</td></tr>
            </tbody>
          </table>
          <span className="xs ink2" style={{ display: 'block', marginTop: 8 }}>
            score = 0.35 D + 0.25 P + 0.20 M + 0.10 R + B{config ? '. Medians of the parts do not add up to the median score.' : ` = ${score}`}
          </span>
        </span>
      )}
    </span>
  );
}
