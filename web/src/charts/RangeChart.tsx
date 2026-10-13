// RangeChart (spec 7.4): median line with a min-max band at ~10 % opacity; one tooltip lists count,
// median, min and max at the hovered date (spec 12.1, Model page).
import { useMemo } from 'react';
import { compact, fmtInt, fmtPLN } from '../lib/format';
import { catColor, useTheme } from '../lib/theme';
import { EChart } from './EChart';
import { baseAxes, palette, tipHead, tipRow, tooltipBox } from './theme';

interface Props {
  dates: string[];
  median: (number | null)[];
  min: (number | null)[];
  max: (number | null)[];
  count: number[];
  label: string;
  className?: string;
}

export function RangeChart({ dates, median, min, max, count, label, className }: Props) {
  const { resolved } = useTheme();
  const option = useMemo(() => {
    const p = palette();
    const c = catColor(1);
    const band = max.map((v, i) => (v != null && min[i] != null ? v - (min[i] as number) : null));
    const single = median.filter((v) => v != null).length === 1;
    let li = -1;
    for (let i = median.length - 1; i >= 0; i--) if (median[i] != null) { li = i; break; }
    return {
      ...baseAxes(p, dates, compact, 'dataMin'),
      grid: { left: 8, right: 72, top: 16, bottom: 36, containLabel: true },
      legend: {
        bottom: 0, left: 0, textStyle: { color: p.ink2, fontSize: 13 },
        data: [{ name: 'Median special price', icon: 'rect' }, { name: 'Min–max range', icon: 'rect' }],
        itemWidth: 14, itemHeight: 8,
      },
      tooltip: {
        ...tooltipBox(p), trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: p.axis, width: 1 } },
        formatter: (params: { dataIndex: number }[]) => {
          const i = params[0]?.dataIndex ?? 0;
          return tipHead(dates[i])
            + tipRow(p.muted, fmtInt(count[i]), 'cars')
            + tipRow(c, fmtPLN(median[i]), 'median special price')
            + tipRow(p.axis, fmtPLN(min[i]), 'min')
            + tipRow(p.axis, fmtPLN(max[i]), 'max');
        },
      },
      series: [
        { type: 'line', name: 'min-base', stack: 'band', data: min, symbol: 'none', lineStyle: { opacity: 0 }, silent: true, tooltip: { show: false } },
        {
          type: 'line', name: 'Min–max range', stack: 'band', data: band, symbol: single ? 'rect' : 'none', symbolSize: [10, 2],
          lineStyle: { opacity: 0 }, areaStyle: { color: c, opacity: 0.1 }, itemStyle: { color: c, opacity: 0.35 }, silent: true,
        },
        {
          type: 'line', name: 'Median special price', z: 3,
          lineStyle: { width: 2, cap: 'round', color: c }, itemStyle: { color: c, borderColor: p.surface, borderWidth: 2 },
          data: median.map((v, i) => ({
            value: v, symbol: i === li || single ? 'circle' : 'none', symbolSize: 10,
            label: i === li ? { show: true, position: 'right', color: p.ink2, fontSize: 12, formatter: () => compact(v) } : undefined,
          })),
        },
      ],
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dates, median, min, max, count, resolved]);
  return <EChart option={option} label={label} className={className} />;
}
