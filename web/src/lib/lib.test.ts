import { describe, expect, it } from 'vitest';
import { toCsv } from './csv';
import { activeCount, filterConfigs, filterOffers, parseFilters, periodSlice } from './filters';
import { compact, fmtDate, fmtInt, fmtPLN, fmtPct, fmtRange } from './format';
import type { Latest } from './types';

const nb = (s: string) => s.replace(/[\u00a0\u202f]/g, ' ');

describe('format (pl-PL)', () => {
  it('formats money with space thousands and zł', () => {
    expect(nb(fmtPLN(120296))).toBe('120 296 zł');
    expect(nb(fmtPLN(1150))).toBe('1 150 zł');
    expect(fmtPLN(null)).toBe('–');
  });
  it('formats percent, ints and dates', () => {
    expect(nb(fmtPct(0.1234)).replace(' %', '%')).toBe('12,3%');
    expect(nb(fmtInt(4768))).toBe('4 768');
    expect(fmtDate('2026-10-13')).toBe('13 paź 2026');
    expect(fmtRange('2026-09-16', '2026-10-13')).toBe('16 wrz – 13 paź 2026');
  });
  it('compacts axis ticks', () => {
    expect(compact(120000)).toBe('120K');
    expect(compact(269500)).toBe('269,5K');
    expect(compact(1200000)).toBe('1,2M');
    expect(nb(compact(4768))).toBe('4 768');
  });
});

describe('filters and URL state', () => {
  it('parses the query string; the dealer filter is private only', () => {
    const f = parseFilters(new URLSearchParams('segment=q&promo=l101,pu,zzz&plan=APL-3&period=6m&retired=1&dealer=9101'));
    expect(f.segment).toBe('Q');
    expect(f.promos).toEqual(['l101', 'pu']);
    expect(f.plans).toEqual(['APL-3']);
    expect(f.period).toBe('6m');
    expect(f.retired).toBe(true);
    expect(f.dealers).toEqual([]);
    expect(activeCount(f)).toBe(4);
  });
  it('configuration rows match a promo when any offer carries the badge', () => {
    const counts = (o: Partial<Record<string, number>>) => ({ bo: 0, fe: 0, l101: 0, pu: 0, be: 0, p15: 0, ...o });
    const rows = [
      { slug: 'q5', segment: 'Q', engine_group: 'TDI', plan_code: 'APL-3', promo_counts: counts({ l101: 3, pu: 1 }) },
      { slug: 'q5', segment: 'Q', engine_group: 'TDI', plan_code: 'APL-3', promo_counts: counts({ l101: 5 }) },
      { slug: 'a3', segment: 'A', engine_group: null, plan_code: 'APL-1', promo_counts: counts({ p15: 3 }) },
    ];
    expect(filterConfigs(rows, parseFilters(new URLSearchParams('promo=l101,pu')))).toHaveLength(1);
    expect(filterConfigs(rows, parseFilters(new URLSearchParams('promo=p15')))).toHaveLength(1);
    expect(filterConfigs(rows, parseFilters(new URLSearchParams('engine=(none)')))[0].slug).toBe('a3');
    expect(filterConfigs(rows, parseFilters(new URLSearchParams('segment=a&plan=APL-1')))).toHaveLength(1);
  });
  it('offer rows combine badges with AND', () => {
    const latest = { directory: { promos: { bo: { badge_bit: 5 }, fe: { badge_bit: 10 }, l101: { badge_bit: 7 }, pu: { badge_bit: 8 }, be: { badge_bit: 9 }, p15: { badge_bit: 6 } } } } as unknown as Latest;
    const rows = [
      { slug: 'q5', segment: 'Q', engine_group: 'TDI', dealer_nr: '1', promo_bits: 1 << 7, plan_code: 'APL-3' },
      { slug: 'q5', segment: 'Q', engine_group: 'TDI', dealer_nr: '1', promo_bits: (1 << 7) | (1 << 8), plan_code: 'APL-3' },
    ];
    expect(filterOffers(rows, parseFilters(new URLSearchParams('promo=l101,pu')), latest)).toHaveLength(1);
  });
  it('slices periods', () => {
    const dates = ['2025-10-13', '2026-04-13', '2026-08-10', '2026-10-13'];
    expect(periodSlice(dates, 'all')).toEqual([0, 4]);
    expect(periodSlice(dates, '3m')).toEqual([2, 4]);
    expect(periodSlice(dates, '12m')).toEqual([0, 4]);
  });
});

describe('edition routing', () => {
  it('the public build has five routes and no private ones', async () => {
    const { ROUTES } = await import('../app/routes');
    expect(ROUTES.map((r) => r.path)).toEqual(['/', '/model/:slug', '/deals', '/changes', '/about']);
  }, 30_000);
  it('the public build reads the public tree from <base>/data/', async () => {
    const { dataUrl } = await import('./data');
    expect(dataUrl('dashboard/latest.json')).toBe('/data/dashboard/latest.json');
  }, 30_000);
});

describe('csv', () => {
  it('quotes and keeps numbers unformatted', () => {
    expect(toCsv(['a', 'b'], [[1234.5, 'x,y'], [null, 'q"']])).toBe('a,b\n1234.5,"x,y"\n,"q"""\n');
  });
});
