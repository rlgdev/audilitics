// One filter row above the content it scopes (spec 7.2). Every control writes the query string.
import { useEffect, useRef, type ReactNode } from 'react';
import { useLatest } from '../app/latest';
import { useData } from '../lib/data';
import { IS_PRIVATE } from '../lib/edition';
import { PLAN_ORDER, PROMO_ORDER, SEGMENT_LABEL, SEGMENT_TO_CODE, activeCount, useUrlState, type Period } from '../lib/filters';
import type { PrivateDealers, Segment } from '../lib/types';

interface Option { value: string; label: string; group?: string }

function Menu({ label, selected, children, onClear }: { label: string; selected: number; children: ReactNode; onClear?: () => void }) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const close = (e: MouseEvent | KeyboardEvent) => {
      const d = ref.current;
      if (!d?.open) return;
      if (e instanceof KeyboardEvent) {
        if (e.key === 'Escape') {
          d.open = false;
          d.querySelector('summary')?.focus();
        }
      } else if (!d.contains(e.target as Node)) d.open = false;
    };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('keydown', close);
    };
  }, []);
  return (
    <details ref={ref} className={`filter${selected ? ' on' : ''}`}>
      <summary aria-label={`${label}${selected ? `, ${selected} selected` : ''}`}>
        {label}{selected ? <span className="count">{selected}</span> : null}
        <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M2 3.5 L5 6.5 L8 3.5" stroke="currentColor" fill="none" strokeWidth="1.5" /></svg>
      </summary>
      <div className="filter-menu">
        {children}
        {onClear && selected > 0 && (
          <div className="menu-actions"><button className="linkbtn" onClick={onClear}>Clear</button></div>
        )}
      </div>
    </details>
  );
}

function MultiMenu({ label, options, value, onChange }: { label: string; options: Option[]; value: string[]; onChange: (v: string[]) => void }) {
  const set = new Set(value);
  let lastGroup: string | undefined;
  return (
    <Menu label={label} selected={value.length} onClear={() => onChange([])}>
      <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
        <legend className="sr-only">{label}</legend>
        {options.map((o) => {
          const head = o.group && o.group !== lastGroup ? <div className="group" key={`g-${o.group}`}>{o.group}</div> : null;
          lastGroup = o.group;
          return (
            <div key={o.value}>
              {head}
              <label>
                <input type="checkbox" checked={set.has(o.value)} onChange={(e) => {
                  const next = new Set(set);
                  if (e.target.checked) next.add(o.value);
                  else next.delete(o.value);
                  onChange(options.map((x) => x.value).filter((v) => next.has(v)));
                }} />
                {o.label}
              </label>
            </div>
          );
        })}
      </fieldset>
    </Menu>
  );
}

function SingleMenu({ label, options, value, onChange }: { label: string; options: Option[]; value: string; onChange: (v: string) => void }) {
  const current = options.find((o) => o.value === value);
  return (
    <Menu label={current && value !== options[0].value ? `${label}: ${current.label}` : label} selected={0}>
      <fieldset style={{ border: 0, margin: 0, padding: 0 }}>
        <legend className="sr-only">{label}</legend>
        {options.map((o) => (
          <label key={o.value}>
            <input type="radio" name={label} checked={o.value === value} onChange={() => onChange(o.value)} />
            {o.label}
          </label>
        ))}
      </fieldset>
    </Menu>
  );
}

export function FilterRow({ hide = [] }: { hide?: ('period' | 'engine' | 'dealer' | 'plan' | 'promo' | 'model' | 'segment')[] }) {
  const latest = useLatest();
  const { filters: f, set, clear } = useUrlState();
  const dealers = useData<PrivateDealers>(IS_PRIVATE ? 'dealers.json' : null, 'private');
  if (!latest) return null;
  const retiredCount = latest.models.filter((m) => m.status === 'retired').length;
  const models = latest.models
    .filter((m) => f.retired || m.status === 'active' || f.models.includes(m.slug))
    .filter((m) => !f.segment || m.segment === f.segment);
  const segOrder: Segment[] = ['A', 'Q', 'S/RS', 'e-tron'];
  const modelOpts: Option[] = segOrder.flatMap((s) => models.filter((m) => m.segment === s)
    .map((m) => ({ value: m.slug, label: m.name.replace(/^Audi /, '') + (m.status === 'retired' ? ' (retired)' : ''), group: SEGMENT_LABEL[s] })));
  const n = activeCount(f);
  return (
    <div className="filters" role="search" aria-label="Filters">
      {!hide.includes('period') && (
        <SingleMenu label="Period" value={f.period} onChange={(v) => set({ period: v === 'all' ? null : (v as Period) })}
          options={[{ value: 'all', label: 'All snapshots' }, { value: '3m', label: 'Last 3 months' }, { value: '6m', label: 'Last 6 months' }, { value: '12m', label: 'Last 12 months' }]} />
      )}
      {!hide.includes('segment') && (
        <SingleMenu label="Segment" value={f.segment ? SEGMENT_TO_CODE[f.segment] : 'all'} onChange={(v) => set({ segment: v === 'all' ? null : v })}
          options={[{ value: 'all', label: 'All segments' }, ...segOrder.map((s) => ({ value: SEGMENT_TO_CODE[s], label: SEGMENT_LABEL[s] }))]} />
      )}
      {!hide.includes('model') && <MultiMenu label="Model" options={modelOpts} value={f.models} onChange={(v) => set({ model: v })} />}
      {!hide.includes('engine') && (
        <MultiMenu label="Engine group" value={f.engines} onChange={(v) => set({ engine: v })}
          options={[...latest.directory.engine_groups.map((e) => ({ value: e, label: e })), { value: '(none)', label: '(not listed)' }]} />
      )}
      {IS_PRIVATE && !hide.includes('dealer') && dealers.data && (
        <MultiMenu label="Dealer" value={f.dealers} onChange={(v) => set({ dealer: v })}
          options={[...dealers.data.dealers].sort((a, b) => (a.name ?? a.nr).localeCompare(b.name ?? b.nr, 'pl'))
            .map((d) => ({ value: d.nr, label: d.name ?? d.nr }))} />
      )}
      {!hide.includes('promo') && (
        <MultiMenu label="Promo" value={f.promos} onChange={(v) => set({ promo: v })}
          options={PROMO_ORDER.map((k) => ({ value: k, label: latest.directory.promos[k].name }))} />
      )}
      {!hide.includes('plan') && (
        <MultiMenu label="Plan" value={f.plans} onChange={(v) => set({ plan: v })} options={PLAN_ORDER.map((p) => ({ value: p, label: p }))} />
      )}
      {retiredCount > 0 && (
        <label className="check">
          <input type="checkbox" checked={f.retired} onChange={(e) => set({ retired: e.target.checked ? '1' : null })} />
          Show retired models ({retiredCount})
        </label>
      )}
      {n > 0 && <button className="linkbtn" onClick={clear}>Clear filters</button>}
    </div>
  );
}
