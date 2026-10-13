// Car (spec 7.1 #/car/:date/:n, private build only): one offer on one date, read from the gzipped snapshot, with
// its configuration's median-price history. No link to audi.pl.
import { useMemo } from 'react';
import { Link, useParams } from 'react-router-dom';
import { RangeChart } from '../../charts/RangeChart';
import { useLatest } from '../../app/latest';
import { EmptyState, ErrorState, Flags, PromoChips } from '../../components/common';
import { ScoreBreakdown } from '../../components/tiles';
import { toRows, useData } from '../../lib/data';
import { fmtDate, fmtInt, fmtPLN, fmtPct } from '../../lib/format';
import type { OfferRow, PrivateDeals, PrivateModelFile, SnapshotFile } from '../../lib/types';

export function Car() {
  const { date = '', n = '' } = useParams();
  const latest = useLatest();
  const offerId = `${date}/${n}`;
  const snap = useData<SnapshotFile>(/^\d{4}-\d{2}-\d{2}$/.test(date) ? `${date}.json.gz` : null, 'snapshots');
  const offer = snap.data?.offers.find((o) => o.offer_id === offerId);
  const slug = offer ? latest?.models.find((m) => m.name === offer.model)?.slug ?? null : null;
  const model = useData<PrivateModelFile>(slug ? `models/${slug}.json` : null, 'private');
  const deals = useData<PrivateDeals>(date === latest?.run.data_date ? 'deals.json' : null, 'private');
  const scored = useMemo(() => toRows<OfferRow>(deals.data).find((o) => o.offer_id === offerId), [deals.data, offerId]);
  const cfg = model.data?.configurations.find((c) => c.config_key === offer?.config_key);

  if (snap.error) return <ErrorState error={snap.error} />;
  if (!snap.data) return <div className="page loading" aria-busy="true"><p className="muted">Loading…</p></div>;
  if (!offer) {
    return (
      <div className="page">
        <h1>Offer not found</h1>
        <EmptyState action={<Link className="btn" to="/offers">Browse offers</Link>}>There is no offer {n} in the run of {fmtDate(date)}.</EmptyState>
      </div>
    );
  }
  const dates = model.data?.dates ?? [];
  const idx = cfg ? dates.map((_, i) => i).filter((i) => cfg.history.special_median[i] != null) : [];
  return (
    <div className="page">
      <div className="page-head">
        <span className="small"><Link to="/offers">Offers</Link>{slug && <> / <Link to={`/model/${slug}`}>{offer.model}</Link></>}</span>
        <h1>{offer.model}</h1>
        <p className="ink2">{offer.engine ?? 'Engine not listed'}. Model year {offer.model_year ?? '–'}, production {offer.production_year ?? '–'}, code {offer.code ?? '–'}. Offer {n} of the run of {fmtDate(date)}, at {offer.dealer ?? offer.dealer_nr}.</p>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'baseline' }}>
          <span style={{ fontSize: 28, fontWeight: 600 }}>{fmtPLN(offer.special)}</span>
          <span className="ink2">catalog {fmtPLN(offer.catalog)}, discount {fmtPct(offer.discount_pct)}, rate {fmtPLN(offer.rate)} net ({offer.plan_code})</span>
        </div>
      </div>
      <dl className="kv">
        <dt>Badges</dt><dd><PromoChips bits={offer.promo_bits} /></dd>
        <dt>30-day price</dt><dd>{fmtPLN(offer.price_30d)}</dd>
        <dt>Deal score</dt><dd>{scored ? <ScoreBreakdown score={scored.score} components={{ D: scored.D, P: scored.P, M: scored.M, R: scored.R, B: scored.B }} /> : 'Scores are kept for the latest run only.'}</dd>
        {scored && <><dt>Flags</dt><dd><Flags flags={scored.flags} /></dd><dt>Identical offers</dt><dd>{fmtInt(scored.identical)}</dd></>}
      </dl>
      <section className="card chart-card">
        <span className="chart-title">Median special price of its configuration</span>
        <span className="chart-sub">{cfg?.label ?? ''}; every run in the private data, PLN gross</span>
        {cfg && idx.length ? (
          <RangeChart dates={idx.map((i) => dates[i])} median={idx.map((i) => cfg.history.special_median[i])}
            min={idx.map((i) => cfg.history.special_min[i])} max={idx.map((i) => cfg.history.special_max[i])}
            count={idx.map((i) => cfg.history.offers[i] ?? 0)} label="Configuration median special price" />
        ) : <p className="muted small">{model.error ? 'History could not be loaded.' : 'Loading history…'}</p>}
      </section>
    </div>
  );
}
