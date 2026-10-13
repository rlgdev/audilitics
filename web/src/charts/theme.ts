// Shared chart anatomy from the tokens (spec 8.3): one y-axis, hairline solid grid, compact ticks,
// text in text tokens only, crosshair tooltip with values first.
import { compact, fmtDate, fmtDayMonth } from '../lib/format';
import { token } from '../lib/theme';
import { esc } from './EChart';

export interface Palette {
  surface: string; ink: string; ink2: string; muted: string; grid: string; axis: string; accent: string;
}

export function palette(): Palette {
  return {
    surface: token('--surface'), ink: token('--ink'), ink2: token('--ink-2'), muted: token('--muted'),
    grid: token('--grid'), axis: token('--axis'), accent: token('--accent'),
  };
}

export function baseAxes(p: Palette, dates: string[], yFormat: (v: number) => string = compact, yMin?: number | 'dataMin') {
  return {
    grid: { left: 8, right: 56, top: 16, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category', data: dates, boundaryGap: false,
      axisLine: { lineStyle: { color: p.axis } }, axisTick: { show: false },
      axisLabel: { color: p.muted, fontSize: 12, formatter: (d: string) => fmtDayMonth(d), hideOverlap: true },
    },
    yAxis: {
      type: 'value', scale: yMin === 'dataMin', min: typeof yMin === 'number' ? yMin : undefined,
      splitLine: { lineStyle: { color: p.grid, width: 1, type: 'solid' } },
      axisLine: { show: false }, axisTick: { show: false },
      axisLabel: { color: p.muted, fontSize: 12, formatter: (v: number) => yFormat(v) },
    },
    textStyle: { fontFamily: 'IBM Plex Sans, system-ui, sans-serif' },
    animation: false,
    aria: { enabled: true },
  };
}

export function tooltipBox(p: Palette) {
  return {
    backgroundColor: p.surface, borderColor: p.axis, borderWidth: 1, padding: [8, 10],
    textStyle: { color: p.ink, fontSize: 13 }, extraCssText: 'border-radius:6px;box-shadow:none;',
    confine: true,
  };
}

/** One tooltip row: line key in the series colour, value first (strong), name second. */
export function tipRow(color: string, value: string, name: string): string {
  return `<div style="display:flex;align-items:center;gap:8px;line-height:20px">`
    + `<span style="width:12px;height:2px;border-radius:1px;background:${color};display:inline-block"></span>`
    + `<strong style="font-variant-numeric:tabular-nums">${esc(value)}</strong>`
    + `<span style="color:var(--ink-2)">${esc(name)}</span></div>`;
}

export function tipHead(date: string): string {
  return `<div style="font-size:12px;color:var(--ink-2);margin-bottom:4px">${esc(fmtDate(date))}</div>`;
}
