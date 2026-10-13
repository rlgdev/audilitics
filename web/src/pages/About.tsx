// About (spec 7.1 #/about): methodology, plan assumptions, promo and score definitions, what is not collected and
// the minimum group size, rules version, last run summary; the source is named as plain text without a link.
import { useLatestState } from '../app/latest';
import { ErrorState, PromoChip } from '../components/common';
import { PLAN_ORDER, PROMO_ORDER } from '../lib/filters';
import { fmtDate, fmtPct } from '../lib/format';

const GLOSSARY: [string, string][] = [
  ['Cena katalogowa (catalog price)', 'List price, PLN gross.'],
  ['Cena specjalna (special price)', 'Discounted stock price, PLN gross.'],
  ['Najniższa cena z 30 dni (30-day price)', 'Lowest price in the 30 days before the reduction, the consumer-law reference price.'],
  ['Rata APL', 'Audi Perfect Lease monthly rate, PLN net, for businesses, calculated from the catalog price.'],
  ['Plan code', 'Which footnote assumptions apply to the rate: APL-1, APL-2, APL-2-EV or APL-3.'],
  ['Promo slider', 'One of the five switches at the bottom of the site’s filter panel; shown here as counts per model.'],
  ['Badge', 'A label on an offer card; the promo filter and chips use badges.'],
  ['Rocznik (model year)', 'Model year; rok produkcji is the production year.'],
  ['Stock cleaning', 'Feed flag that feeds the best-offer and insurance rules.'],
  ['Offer', 'One car listed on one date. Offers have no identity across runs.'],
  ['Configuration', 'Model, engine, model code and model year: the unit compared across runs and the unit published here.'],
  ['Like-for-like index', 'Median price change of configurations present in two consecutive runs, chained from 100.'],
  ['Net added / removed', 'Sum of the increases and decreases of offer counts per configuration; a lower bound of turnover.'],
  ['Hot deal', 'A configuration whose median price improved within the last 31 days.'],
  ['Retired model', 'A model with no offers for three consecutive runs; hidden by default, history kept.'],
];

export function About() {
  const { data: latest, error } = useLatestState();
  if (error) return <ErrorState error={error} />;
  if (!latest) return <p className="muted">Loading…</p>;
  const d = latest.directory;
  const s = d.scoring;
  return (
    <div className="page prose">
      <h1>About this dashboard</h1>
      <p>Audilitics shows price trends in the “gotowe do odbioru” stock of the Audi Polska website gotowedoodbioru.audi.pl, collected every 14 days. Everything here is an aggregate: model and segment statistics, and configurations (model, engine, model code and model year) with at least {d.min_group} priced offers.</p>
      <p><strong>The figures are aggregates of offers published on the source site on the stated dates. They are not offers within the meaning of the Civil Code.</strong> Ask an Audi dealer for current offers. The project is not affiliated with Audi or Volkswagen Group Polska and links to no offer.</p>

      <h2>What is collected and what is not</h2>
      <p>Not collected, stored or derived: {d.not_collected.join(', ')}. These fields are dropped from the feed as soon as it is read. Single cars are therefore never followed from one run to the next; everything that compares runs works on configurations.</p>
      <p>Every price, discount, rate or score shown rests on at least {d.min_group} priced offers. A configuration with fewer has no row on that date, though its offers still count in model, segment and total counts.</p>

      <h2>Data</h2>
      <table>
        <tbody>
          <tr><th scope="row">Latest data</th><td>{fmtDate(latest.run.data_date)}</td></tr>
          <tr><th scope="row">Last run</th><td>{fmtDate(latest.run.date)}, status {latest.run.status}, fetch took {latest.run.duration_s ?? '–'} s</td></tr>
          <tr><th scope="row">Next run</th><td>{fmtDate(latest.run.next_run)}</td></tr>
          <tr><th scope="row">Runs</th><td>{latest.run.snapshots_ok}</td></tr>
          <tr><th scope="row">Rules version</th><td>{latest.run.rules_version}</td></tr>
          <tr><th scope="row">Site bundle hash</th><td>{latest.run.bundle_hash}</td></tr>
          <tr><th scope="row">Collector</th><td>{latest.run.collector_version}</td></tr>
          <tr><th scope="row">Source</th><td>gotowedoodbioru.audi.pl (Audi Polska stock website), read with at most 10 requests per run</td></tr>
        </tbody>
      </table>

      <h2>Payment plans behind the rate</h2>
      <p>The site shows one Audi Perfect Lease rate per offer: net, for businesses, calculated from the catalog price. The footnote the site assigns selects the plan.</p>
      <table>
        <thead><tr><th>Plan</th><th>Footnote</th><th>Initial fee</th><th>Term</th><th>Mileage per year</th></tr></thead>
        <tbody>
          {PLAN_ORDER.map((p) => d.plans[p] && (
            <tr key={p}><td>{p}</td><td>{d.plans[p].footnote}</td><td>{fmtPct(d.plans[p].fee_pct)} of catalog price</td><td>{d.plans[p].term_months} months</td><td>{d.plans[p].mileage_km.toLocaleString('pl-PL')} km</td></tr>
          ))}
        </tbody>
      </table>
      <p className="small ink2">APL-2-EV is the footnote 2 exception for electric models of model year 2026 and the A6 e-tron and Q6 e-tron ranges. Leasing 101% ({d.leasing_101 ? `${fmtPct(d.leasing_101.fee_pct)} initial fee, ${d.leasing_101.term_months} months, ${fmtPct(d.leasing_101.residual_pct)} residual` : 'see footnote'}) is a flag, not a rate.</p>
      {Object.entries(d.plan_footnotes).map(([k, t]) => <p key={k} className="small ink2" lang="pl"><sup>{k}</sup> {t}</p>)}

      <h2>Promos</h2>
      <p>Promo names are the site’s own wording. Chips and the promo filter use the badges on the offer cards; a configuration matches a promo when at least one of its offers carries the badge, and the number next to a chip counts those offers. The site’s own slider numbers appear as counts per model.</p>
      <table>
        <tbody>
          {PROMO_ORDER.map((k) => (
            <tr key={k}><td><PromoChip promo={k} /></td><td lang="pl" className="small">{d.promos[k].footnote}</td></tr>
          ))}
        </tbody>
      </table>

      <h2>Deal score</h2>
      <p>Every priced offer gets a score from 0 to 100; a configuration shows its best and median score and the median of each part. Percentiles are taken within the same model unless stated.</p>
      <table>
        <thead><tr><th>Part</th><th>Weight</th><th>Definition</th></tr></thead>
        <tbody>
          <tr><td>Discount depth D</td><td>{s.weights.D}</td><td>Percentile rank of the discount %.</td></tr>
          <tr><td>Price position P</td><td>{s.weights.P}</td><td>100 minus the percentile rank of the special price within the same model and engine group.</td></tr>
          <tr><td>Momentum M</td><td>{s.weights.M}</td><td>Fall of the configuration’s median special price since the previous run: 0 % scores 0, {fmtPct(s.momentum_cap_pct)} or more scores 100; a configuration that is new or had fewer than {d.min_group} priced offers scores {s.momentum_new_car}.</td></tr>
          <tr><td>Rate value R</td><td>{s.weights.R}</td><td>100 minus the percentile rank of rate ÷ special price within the same model and plan.</td></tr>
          <tr><td>Promo bonus B</td><td>up to 10</td><td>Insurance for 1 zł +{s.promo_bonus.pu}; Final Edition or +15 000 zł badge +{s.promo_bonus.fe_or_p15}; best-offer badge +{s.promo_bonus.bo}.</td></tr>
        </tbody>
      </table>
      <p>score = 0.35 D + 0.25 P + 0.20 M + 0.10 R + B, rounded. Flags: lowest price seen for the configuration, biggest median drop in its model this run, new configuration.</p>
      <p>A <strong>hot deal</strong> is a configuration in stock whose median special price fell by {fmtPct(s.hot.hot_drop_pct)} or {s.hot.hot_drop_pln.toLocaleString('pl-PL')} zł or more within the last {s.hot.hot_window_days} days, reached its lowest price inside that window after a fall, or is new in the window with a best score of {s.hot.hot_new_score} or more.</p>

      <h2>Glossary</h2>
      <table><tbody>{GLOSSARY.map(([t, m]) => <tr key={t}><th scope="row">{t}</th><td>{m}</td></tr>)}</tbody></table>
    </div>
  );
}
