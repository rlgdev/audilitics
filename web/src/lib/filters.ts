// Filter state lives in the query string (spec 7.2): #/deals?segment=q&promo=l101,pu
import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { IS_PRIVATE } from './edition';
import type { Latest, PlanCode, PromoCounts, PromoKey, Segment } from './types';

export type Period = '3m' | '6m' | '12m' | 'all';

export const SEGMENT_CODES: Record<string, Segment> = { a: 'A', q: 'Q', s: 'S/RS', e: 'e-tron' };
export const SEGMENT_TO_CODE: Record<Segment, string> = { A: 'a', Q: 'q', 'S/RS': 's', 'e-tron': 'e' };
export const SEGMENT_LABEL: Record<Segment, string> = { A: 'A (A3–A8)', Q: 'Q', 'S/RS': 'S / RS', 'e-tron': 'e-tron' };
export const PROMO_ORDER: PromoKey[] = ['bo', 'fe', 'l101', 'pu', 'be', 'p15'];
export const PLAN_ORDER: PlanCode[] = ['APL-1', 'APL-2', 'APL-2-EV', 'APL-3'];

export interface Filters {
  period: Period;
  segment: Segment | null;
  models: string[];
  engines: string[];
  dealers: string[];
  promos: PromoKey[];
  plans: PlanCode[];
  retired: boolean;
}

const list = (v: string | null): string[] => (v ? v.split(',').filter(Boolean) : []);

export function parseFilters(sp: URLSearchParams): Filters {
  const period = sp.get('period');
  return {
    period: period === '3m' || period === '6m' || period === '12m' ? period : 'all',
    segment: SEGMENT_CODES[sp.get('segment') ?? ''] ?? null,
    models: list(sp.get('model')),
    engines: list(sp.get('engine')),
    dealers: IS_PRIVATE ? list(sp.get('dealer')) : [], // the dealer filter exists in the private build only
    promos: list(sp.get('promo')).filter((p): p is PromoKey => (PROMO_ORDER as string[]).includes(p)),
    plans: list(sp.get('plan')).filter((p): p is PlanCode => (PLAN_ORDER as string[]).includes(p)),
    retired: sp.get('retired') === '1',
  };
}

export function activeCount(f: Filters): number {
  return (f.period !== 'all' ? 1 : 0) + (f.segment ? 1 : 0) + (f.models.length ? 1 : 0) + (f.engines.length ? 1 : 0)
    + (f.dealers.length ? 1 : 0) + (f.promos.length ? 1 : 0) + (f.plans.length ? 1 : 0);
}

const FILTER_KEYS = ['period', 'segment', 'model', 'engine', 'dealer', 'promo', 'plan'];

/** URL state: get/set any query key; setting '' or [] removes it. History entries are pushed so Back works. */
export function useUrlState() {
  const [sp, setSp] = useSearchParams();
  const filters = useMemo(() => parseFilters(sp), [sp]);
  const set = useCallback((patch: Record<string, string | string[] | null>, replace = false) => {
    setSp((prev) => {
      const next = new URLSearchParams(prev);
      for (const [k, v] of Object.entries(patch)) {
        const s = Array.isArray(v) ? v.join(',') : v;
        if (s == null || s === '') next.delete(k);
        else next.set(k, s);
      }
      return next;
    }, { replace });
  }, [setSp]);
  const clear = useCallback(() => set(Object.fromEntries(FILTER_KEYS.map((k) => [k, null]))), [set]);
  return { sp, filters, set, clear };
}

export function badgeBit(key: PromoKey, latest: Latest | null): number {
  return latest?.directory.promos[key]?.badge_bit ?? -1;
}

export function hasBadge(bits: number, key: PromoKey, latest: Latest | null): boolean {
  const b = badgeBit(key, latest);
  return b >= 0 && ((bits >> b) & 1) === 1;
}

export function badgePromos(bits: number, latest: Latest | null): PromoKey[] {
  return PROMO_ORDER.filter((k) => hasBadge(bits, k, latest));
}

interface ConfigLike { slug: string; segment: string; engine_group: string | null; plan_code: string; promo_counts?: PromoCounts }

/** Configuration rows (spec 7.2): a configuration matches a promo when at least one of its offers carries the
 * badge, so selected badges each need a positive count. */
export function filterConfigs<T extends ConfigLike>(rows: T[], f: Filters): T[] {
  const models = new Set(f.models);
  const engines = new Set(f.engines);
  const plans = new Set<string>(f.plans);
  return rows.filter((r) => {
    if (f.segment && r.segment !== f.segment) return false;
    if (models.size && !models.has(r.slug)) return false;
    if (engines.size && !engines.has(r.engine_group ?? '(none)')) return false;
    if (plans.size && !plans.has(r.plan_code)) return false;
    for (const k of f.promos) if (!r.promo_counts || !(r.promo_counts[k] > 0)) return false;
    return true;
  });
}

interface OfferLike { slug: string; segment: string; engine_group: string | null; dealer_nr: string | null; promo_bits: number; plan_code: string }

/** Offer rows (private build): every filter applies per offer; selected badges combine with AND, like the site. */
export function filterOffers<T extends OfferLike>(rows: T[], f: Filters, latest: Latest | null): T[] {
  const models = new Set(f.models);
  const engines = new Set(f.engines);
  const dealers = new Set(f.dealers);
  const plans = new Set<string>(f.plans);
  const bits = f.promos.map((k) => badgeBit(k, latest));
  return rows.filter((r) => {
    if (f.segment && r.segment !== f.segment) return false;
    if (models.size && !models.has(r.slug)) return false;
    if (engines.size && !engines.has(r.engine_group ?? '(none)')) return false;
    if (dealers.size && !dealers.has(r.dealer_nr ?? '')) return false;
    if (plans.size && !plans.has(r.plan_code)) return false;
    for (const b of bits) if (b < 0 || ((r.promo_bits >> b) & 1) !== 1) return false;
    return true;
  });
}

/** Indices of dates inside the period filter (spec 7.2); "all" keeps every snapshot. */
export function periodSlice(dates: string[], period: Period): [number, number] {
  if (period === 'all' || dates.length === 0) return [0, dates.length];
  const months = period === '3m' ? 3 : period === '6m' ? 6 : 12;
  const last = new Date(`${dates[dates.length - 1]}T00:00:00Z`);
  last.setUTCMonth(last.getUTCMonth() - months);
  const cut = last.toISOString().slice(0, 10);
  const start = dates.findIndex((d) => d >= cut);
  return [start < 0 ? 0 : start, dates.length];
}
