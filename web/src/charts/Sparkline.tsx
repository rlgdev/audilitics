// Sparkline: plain SVG (53 tiles would be too heavy as ECharts instances). 2 px line, end dot with a
// surface ring; a single point renders as a dot.

interface Props {
  data: (number | null)[];
  width?: number;
  height?: number;
  slot?: number;
  label?: string;
}

export function Sparkline({ data, width = 120, height = 28, slot = 1, label }: Props) {
  const pts = data.map((v, i) => [i, v] as const).filter((p): p is readonly [number, number] => p[1] != null);
  if (pts.length === 0) return <svg width={width} height={height} aria-hidden="true" />;
  const vals = pts.map((p) => p[1]);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const pad = 5;
  const n = Math.max(data.length - 1, 1);
  const x = (i: number) => (data.length === 1 ? width - pad : pad + (i / n) * (width - 2 * pad));
  const y = (v: number) => (hi === lo ? height / 2 : pad + (1 - (v - lo) / (hi - lo)) * (height - 2 * pad));
  const d = pts.map((p, k) => `${k === 0 ? 'M' : 'L'}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join(' ');
  const last = pts[pts.length - 1];
  const color = `var(--cat-${slot})`;
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role={label ? 'img' : undefined} aria-label={label} aria-hidden={label ? undefined : true}>
      {pts.length > 1 && <path d={d} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />}
      <circle cx={x(last[0])} cy={y(last[1])} r={4} fill={color} stroke="var(--surface)" strokeWidth={2} />
    </svg>
  );
}
