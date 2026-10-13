// Offers tab of the Model page (private build only).
import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLatest } from '../../app/latest';
import { EmptyState, ErrorState } from '../../components/common';
import { DataTable } from '../../components/DataTable';
import { offerColumns } from '../../components/tables';
import { toRows, useData } from '../../lib/data';
import { filterOffers, useUrlState } from '../../lib/filters';
import type { OfferRow, PrivateModelFile } from '../../lib/types';
import { carPath } from './Offers';

export function ModelOffers({ slug }: { slug: string }) {
  const latest = useLatest();
  const navigate = useNavigate();
  const file = useData<PrivateModelFile>(`models/${slug}.json`, 'private');
  const { filters: f } = useUrlState();
  const rows = useMemo(() => filterOffers(toRows<OfferRow>(file.data?.offers), { ...f, models: [], segment: null }, latest),
    [file.data, f, latest]);
  const columns = useMemo(() => offerColumns(latest), [latest]);
  if (file.error) return <ErrorState error={file.error} />;
  if (!file.data) return <p className="muted">Loading…</p>;
  if (!rows.length) return <EmptyState>No offers match these filters.</EmptyState>;
  return (
    <DataTable noun={['offer', 'offers']} rows={rows} columns={columns} rowKey={(r) => r.offer_id} storageKey="model-offers" csvName={`audilitics-${slug}-offers.csv`}
      defaultSort={{ id: 'special', desc: false }} onRowClick={(r) => navigate(carPath(r.offer_id))} caption={`Offers of ${file.data.model.name}`} height={560} />
  );
}
