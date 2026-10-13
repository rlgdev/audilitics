// pl-PL formatting (spec 7.5): space thousands, "zł", dates like "13 paź 2026".

const int = new Intl.NumberFormat('pl-PL', { maximumFractionDigits: 0, useGrouping: 'always' } as unknown as Intl.NumberFormatOptions);
const dec1 = new Intl.NumberFormat('pl-PL', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const pct1 = new Intl.NumberFormat('pl-PL', { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 });
const dateFmt = new Intl.DateTimeFormat('pl-PL', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Europe/Warsaw' });
const dayMonth = new Intl.DateTimeFormat('pl-PL', { day: 'numeric', month: 'short', timeZone: 'Europe/Warsaw' });

const DASH = '–';

export function fmtInt(n: number | null | undefined): string {
  return n == null || Number.isNaN(n) ? DASH : int.format(Math.round(n));
}

export function fmtPLN(n: number | null | undefined): string {
  return n == null ? DASH : `${int.format(Math.round(n))} zł`;
}

export function fmtPct(n: number | null | undefined): string {
  return n == null ? DASH : pct1.format(n);
}

export function fmtDec(n: number | null | undefined): string {
  return n == null ? DASH : dec1.format(n);
}

export function signed(n: number, fmt: (x: number) => string): string {
  if (n === 0) return fmt(0);
  return (n > 0 ? '+' : '−') + fmt(Math.abs(n));
}

/** ISO date (YYYY-MM-DD) -> "13 paź 2026". Dates are UTC run dates; noon avoids any day shift. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return DASH;
  return dateFmt.format(new Date(`${iso}T12:00:00Z`));
}

export function fmtDayMonth(iso: string): string {
  return dayMonth.format(new Date(`${iso}T12:00:00Z`));
}

/** "16 wrz – 13 paź 2026" */
export function fmtRange(a: string, b: string): string {
  if (a === b) return fmtDate(b);
  const sameYear = a.slice(0, 4) === b.slice(0, 4);
  return `${sameYear ? fmtDayMonth(a) : fmtDate(a)} – ${fmtDate(b)}`;
}

/** Axis ticks and KPI values: 120K, 1,2M (spec 8.3). */
export function compact(n: number | null | undefined): string {
  if (n == null) return DASH;
  const a = Math.abs(n);
  if (a >= 1_000_000) return `${dec1.format(n / 1_000_000).replace(/,0$/, '')}M`;
  if (a >= 10_000) {
    const k = Math.round(n / 100) / 10;
    return `${Number.isInteger(k) ? int.format(k) : dec1.format(k)}K`;
  }
  return int.format(n);
}

export function daysBetween(a: string, b: string): number {
  return Math.round((Date.parse(`${b}T00:00:00Z`) - Date.parse(`${a}T00:00:00Z`)) / 86_400_000);
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
