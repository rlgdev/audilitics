// TrendChart (spec 7.4): ECharts line, crosshair tooltip listing every series at the date, one y-axis,
// 2 px lines, 8 px end markers with a 2 px surface ring, legend when 2+ series, direct label on the endpoint.
import { useMemo } from 'react';
import { compact } from '../lib/format';
import { catColor, useTheme } from '../lib/theme';
import { EChart } from './EChart';
import { baseAxes, palette, tipHead, tipRow, tooltipBox } from './theme';

export interface TrendSeries {
  name: string;
  data: (number | null)[];
  slot?: number; // categorical slot 1-8; 0 or undefined with muted=true -> grey
  muted?: boolean;
}

interface Props {
  dates: string[];
  series: TrendSeries[];
  format: (v: number | null) => string;
  axisFormat?: (v: number) => string;
  label: string;
  className?: string;
  yMin?: number | 'dataMin';
  endLabels?: boolean;
}

export function TrendChart({ dates, series, format, axisFormat = compact, label, className, yMin = 'dataMin', endLabels = true }: Props) {
  const { resolved } = useTheme();
  const option = useMemo(() => {
    const p = palette();
    const colors = series.map((s) => (s.muted ? p.muted : catColor(s.slot ?? 1)));
    const lastIdx = (d: (number | null)[]) => {
      for (let i = d.length - 1; i >= 0; i--) if (d[i] != null) return i;
      return -1;
    };
    const showLegend = series.length >= 2;
    return {
      ...baseAxes(p, dates, axisFormat, yMin),
      grid: { left: 8, right: endLabels ? 72 : 16, top: 16, bottom: showLegend ? 40 : 8, containLabel: true },
      legend: showLegend ? {
        bottom: 0, left: 0, icon: 'rect', itemWidth: 14, itemHeight: 3,
        textStyle: { color: p.ink2, fontSize: 13 }, data: series.map((s) => s.name),
      } : { show: false },
      tooltip: {
        ...tooltipBox(p), trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: p.axis, width: 1 } },
        formatter: (params: { dataIndex: number }[]) => {
          const i = params[0]?.dataIndex ?? 0;
          return tipHead(dates[i]) + series.map((s, k) => tipRow(colors[k], format(s.data[i]), s.name)).join('');
        },
      },
      series: series.map((s, k) => {
        const li = lastIdx(s.data);
        const single = s.data.filter((v) => v != null).length === 1;
        return {
          type: 'line', name: s.name, connectNulls: false, smooth: false,
          lineStyle: { width: 2, cap: 'round', join: 'round', color: colors[k] },
          itemStyle: { color: colors[k], borderColor: p.surface, borderWidth: 2 },
          emphasis: { disabled: true },
          z: s.muted ? 1 : 3,
          data: s.data.map((v, i) => ({
            value: v,
            symbol: i === li || single ? 'circle' : 'none',
            symbolSize: 10,
            label: endLabels && i === li && !s.muted ? {
              show: true, position: 'right', color: p.ink2, fontSize: 12, formatter: () => compact(v),
            } : undefined,
          })),
        };
      }),
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dates, series, format, axisFormat, yMin, endLabels, resolved]);
  return <EChart option={option} label={label} className={className} />;
}
