// Small shared components: EmptyState, ErrorState, Delta, PromoChip, Flags, ThemeToggle, ShowData (spec 7.4).
import { useId, useState, type ReactNode } from 'react';
import { useLatest } from '../app/latest';
import { PROMO_ORDER, badgePromos } from '../lib/filters';
import { fmtInt } from '../lib/format';
import { useTheme, type ThemeChoice } from '../lib/theme';
import type { PromoCounts, PromoKey } from '../lib/types';

export function EmptyState({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty" role="status">
      <p>{children}</p>
      {action}
    </div>
  );
}

export function ErrorState({ error, retry }: { error: Error; retry?: () => void }) {
  return (
    <div className="empty error" role="alert">
      <p>The data could not be loaded ({error.message}). Check your connection and try again.</p>
      {retry && <button className="btn" onClick={retry}>Try again</button>}
    </div>
  );
}

/** Signed change with an arrow icon and colour by direction x whether up is good (spec 8.1 status colours). */
export function Delta({ value, format, upIsGood = true, suffix }: { value: number | null | undefined; format: (n: number) => string; upIsGood?: boolean; suffix?: string }) {
  if (value == null) return null;
  if (value === 0) return <span className="delta flat">no change{suffix ? ` ${suffix}` : ''}</span>;
  const up = value > 0;
  const good = up === upIsGood;
  return (
    <span className={`delta ${good ? 'good' : 'bad'}`}>
      <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
        <path d={up ? 'M5 1 L9 8 L1 8 Z' : 'M5 9 L9 2 L1 2 Z'} fill="currentColor" />
      </svg>
      <span>{up ? '+' : '−'}{format(Math.abs(value))}</span>
      <span className="sr-only">{up ? 'up' : 'down'}</span>
      {suffix && <span className="ink2">{suffix}</span>}
    </span>
  );
}

export function PromoChip({ promo, count }: { promo: PromoKey; count?: number }) {
  const latest = useLatest();
  const def = latest?.directory.promos[promo];
  if (!def) return null;
  return (
    <span className="chip" title={def.footnote ?? def.name}>
      <span className="swatch" style={{ background: `var(--cat-${def.slot})` }} aria-hidden="true" />
      {def.name}
      {count != null && <span className="ink2 num">{fmtInt(count)}</span>}
    </span>
  );
}

/** Badges of one offer (private build). */
export function PromoChips({ bits, max = 6 }: { bits: number; max?: number }) {
  const latest = useLatest();
  const keys = badgePromos(bits, latest);
  if (!keys.length) return <span className="muted">–</span>;
  return (
    <span className="chips">
      {keys.slice(0, max).map((k) => <PromoChip key={k} promo={k} />)}
      {keys.length > max && <span className="chip">+{keys.length - max}</span>}
    </span>
  );
}

/** Badge counts of a configuration: chips with the number of offers carrying each badge. */
export function PromoCountChips({ counts, max = 6 }: { counts: PromoCounts; max?: number }) {
  if (!counts) return <span className="muted">–</span>;
  const keys = PROMO_ORDER.filter((k) => counts[k] > 0).sort((a, b) => counts[b] - counts[a]);
  if (!keys.length) return <span className="muted">–</span>;
  return (
    <span className="chips">
      {keys.slice(0, max).map((k) => <PromoChip key={k} promo={k} count={counts[k]} />)}
      {keys.length > max && <span className="chip">+{keys.length - max}</span>}
    </span>
  );
}

const FLAG_TEXT: Record<string, string> = {
  lowest_ever: 'Lowest price seen',
  biggest_drop_this_run: 'Biggest drop in model',
  new_config: 'New configuration',
  last_one: 'Last one of its version',
};

export function Flags({ flags }: { flags: string[] }) {
  if (!flags.length) return null;
  return <span className="chips">{flags.map((f) => <span key={f} className="flag">{FLAG_TEXT[f] ?? f}</span>)}</span>;
}

export function ThemeToggle() {
  const { choice, setChoice } = useTheme();
  const opts: [ThemeChoice, string][] = [['light', 'Light'], ['dark', 'Dark'], ['system', 'System']];
  return (
    <div className="seg" role="group" aria-label="Colour theme">
      {opts.map(([v, l]) => (
        <button key={v} type="button" aria-pressed={choice === v} onClick={() => setChoice(v)}>{l}</button>
      ))}
    </div>
  );
}

/** "Show data" toggle: every chart has a table view (spec 8.3). */
export function ShowData({ children, label = 'Show data' }: { children: ReactNode; label?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div>
      <button className="linkbtn" aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}>
        {open ? 'Hide data' : label}
      </button>
      {open && <div id={id} style={{ marginTop: 8 }}>{children}</div>}
    </div>
  );
}

export function SimpleTable({ headers, rows, numeric = [] }: { headers: string[]; rows: (string | number)[][]; numeric?: number[] }) {
  return (
    <div className="dt" style={{ maxHeight: 320 }}>
      <table>
        <thead><tr>{headers.map((h, i) => <th key={h + i} className={numeric.includes(i) ? 'r' : ''} scope="col">{h}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, k) => (
            <tr key={k} style={{ cursor: 'default' }}>{r.map((c, i) => <td key={i} className={numeric.includes(i) ? 'r' : ''}>{c}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
