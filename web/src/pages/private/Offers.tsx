// Offers (spec 7.1 #/offers, private build only): ranked offers with score breakdown, flags, promo chips; segment
// tabs; hot=1 lists the offers of hot configurations. No VIN or link column exists.
import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLatest } from '../../app/latest';
import { EmptyState, ErrorState } from '../../components/common';
import { DataTable } from '../../components/DataTable';
import { FilterRow } from '../../components/FilterRow';
import { offerColumns } from '../../components/tables';
import { toRows, useData } from '../../lib/data';
import { SEGMENT_LABEL, SEGMENT_TO_CODE, filterOffers, useUrlState } from '../../lib/filters';
import type { OfferRow, PrivateDeals, Segment } from '../../lib/types';

const SEGS: Segment[] = ['A', 'Q', 'S/RS', 'e-tron'];

export function carPath(offerId: string): string {
  const [date, n] = offerId.split('/');
  return `/car/${date}/${n}`;
}

export function Offers() {
  const latest = useLatest();
  const navigate = useNavigate();
  const deals = useData<PrivateDeals>('deals.json', 'private');
  const { sp, filters: f, set } = useUrlState();
  const hot = sp.get('hot') === '1';
  const all = useMemo(() => toRows<OfferRow>(deals.data), [deals.data]);
  const visible = useMemo(() => {
    const r = filterOffers(all, f, latest);
    return hot ? r.filter((o) => o.hot) : r;
  }, [all, f, latest, hot]);
  const columns = useMemo(() => offerColumns(latest), [latest]);
  if (deals.error) return <ErrorState error={deals.error} />;
  return (
    <div className={`page${deals.loading ? ' loading' : ''}`}>
      <div className="page-head">
        <h1>Offers</h1>
        <p className="ink2">Private build: every scored offer of the latest run, ranked by deal score. Offers have no identity across runs; open one to see its configuration’s history.</p>
        <FilterRow hide={['period', 'segment']} />
      </div>
      <div className="tabs" role="tablist" aria-label="Segment">
        {[null, ...SEGS].map((s) => (
          <button key={s ?? 'all'} role="tab" aria-selected={f.segment === s} onClick={() => set({ segment: s ? SEGMENT_TO_CODE[s] : null })}>
            {s ? SEGMENT_LABEL[s] : 'All segments'}
          </button>
        ))}
      </div>
      <label className="check"><input type="checkbox" checked={hot} onChange={(e) => set({ hot: e.target.checked ? '1' : null })} /> Offers of hot configurations only</label>
      {!deals.data ? <p className="muted">Loading…</p> : visible.length === 0 ? <EmptyState>No offers match these filters.</EmptyState> : (
        <DataTable noun={['offer', 'offers']} rows={visible} columns={columns} rowKey={(r) => r.offer_id} storageKey="offers" csvName="audilitics-offers.csv"
          defaultSort={{ id: 'score', desc: true }} onRowClick={(r) => navigate(carPath(r.offer_id))} caption="Offers" height={640} />
      )}
    </div>
  );
}
