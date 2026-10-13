// PromoMixChart (spec 7.4): cars per promo per snapshot, one fixed colour per promo, 2 px surface gaps.
// Promos overlap (one car can carry several), so the bars are grouped side by side rather than stacked:
// a stack would read as parts of a whole (dataviz rule, spec 8.3; see ADR-0007).
import { useMemo } from 'react';
import { fmtInt } from '../lib/format';
import { catColor, useTheme } from '../lib/theme';
import type { PromoDef, PromoKey } from '../lib/types';
import { EChart } from './EChart';
import { baseAxes, palette, tipHead, tipRow, tooltipBox } from './theme';

interface Props {
  dates: string[];
  counts: Record<string, number[]>;
  promos: Record<PromoKey, PromoDef>;
  order: PromoKey[];
  label: string;
  className?: string;
}

export function PromoMixChart({ dates, counts, promos, order, label, className }: Props) {
  const { resolved } = useTheme();
  const option = useMemo(() => {
    const p = palette();
    const keys = order.filter((k) => (counts[k] ?? []).some((v) => v > 0));
    const axes = baseAxes(p, dates, (v) => fmtInt(v), 0);
    return {
      ...axes,
      xAxis: { ...axes.xAxis, boundaryGap: true },
      grid: { left: 8, right: 16, top: 16, bottom: 40, containLabel: true },
      legend: {
        bottom: 0, left: 0, icon: 'rect', itemWidth: 10, itemHeight: 10, textStyle: { color: p.ink2, fontSize: 12 },
        data: keys.map((k) => promos[k].name),
      },
      tooltip: {
        ...tooltipBox(p), trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(137,135,129,0.08)' } },
        formatter: (params: { dataIndex: number }[]) => {
          const i = params[0]?.dataIndex ?? 0;
          return tipHead(dates[i]) + keys.map((k) => tipRow(catColor(promos[k].slot), fmtInt(counts[k][i]), promos[k].name)).join('');
        },
      },
      series: keys.map((k) => ({
        type: 'bar', name: promos[k].name, data: counts[k], barMaxWidth: 24, barGap: '0%',
        itemStyle: { color: catColor(promos[k].slot), borderRadius: [4, 4, 0, 0], borderColor: p.surface, borderWidth: 1 },
        emphasis: { itemStyle: { opacity: 0.85 } },
      })),
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dates, counts, promos, order, resolved]);
  return <EChart option={option} label={label} className={className} />;
}
