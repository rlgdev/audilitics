// Shapes of the JSON files written by the collector (spec 5.3). Keep in sync with collector/collector/public.py
// (public tree) and indexes.py (private tree).

export type Segment = 'A' | 'Q' | 'S/RS' | 'e-tron';
export type PromoKey = 'bo' | 'fe' | 'l101' | 'pu' | 'be' | 'p15';
export type PlanCode = 'APL-1' | 'APL-2' | 'APL-2-EV' | 'APL-3';
export type Series = (number | null)[];
export type PromoCounts = Record<PromoKey, number> | null;
export interface Components { D: number | null; P: number | null; M: number | null; R: number | null; B: number | null }

export interface ModelTile {
  slug: string; name: string; segment: Segment; status: 'active' | 'retired'; order: number; offers: number;
  delta: number | null; priced: number; special_min: number | null;
  spark: { special_median: Series; priced: number[] }; promos: PromoKey[]; engine_groups: string[];
  first_seen: string; retired_on: string | null;
}

export interface PricePoint { date: string; special_median: number; priced: number }

export interface ConfigInfo {
  config_key: string; label: string; model: string; slug: string; segment: Segment; engine: string | null;
  engine_group: string | null; code: string | null; model_year: string | null; plan_code: PlanCode;
}

export interface ConfigRow extends ConfigInfo {
  offers: number; priced: number; catalog_median: number | null; special_min: number | null;
  special_median: number | null; special_max: number | null; price_30d_median: number | null;
  discount_pct_median: number | null; discount_pct_max: number | null; rate_min: number | null; term: number | null;
  initial_fee: number | null; score_best: number | null; score_median: number | null; components: Components | null;
  offers_80: number | null; promo_counts: PromoCounts; flags: string[]; hot: boolean; hot_score: number | null;
  drop: number | null; drop_pct: number | null;
}

export interface HotConfig extends ConfigInfo {
  offers: number; priced: number; special_median: number; start_price: number; drop: number; drop_pct: number;
  score_best: number; hot_score: number; flags: string[]; reasons: string[]; promo_counts: PromoCounts;
  points: PricePoint[];
}

export interface PromoDef { name: string; slot: number; badge_bit: number; footnote: string | null }
export interface PlanDef { footnote: number; fee_pct: number; term_months: number; mileage_km: number }
export interface ModelEvent { model: string; slug: string; segment: Segment; cars_now: number; first_seen: string; last_seen: string | null; possible_rename_of: string | null }

export interface ChangesSummary {
  configs_new: number; configs_gone: number; price_drops: number; price_rises: number; stock: number;
  promo_changes: number; median_drop_pct: number | null; priced: number;
  largest_drop: { label: string; config_key: string; diff: number; pct: number } | null;
  models_most_added: { model: string; slug: string; net_added: number }[]; first_run: boolean;
  models_new: number; models_retired: number; models_returned: number;
}

export interface Latest {
  run: {
    date: string | null; status: 'ok' | 'suspect' | 'failed' | null; data_date: string | null; next_run: string | null;
    rules_version: string | null; bundle_hash: string | null; duration_s: number | null; snapshots_ok: number;
    collector_version: string; stale_after_days: number;
  };
  kpis: {
    offers: { value: number | null; delta: number | null; spark: Series };
    models: { value: number | null; delta: number | null; spark: Series };
    discount_pct_median: { discount_pct_median: number | null; priced: number };
    rate_min: { rate_min: number | null; plan_code: PlanCode | null; model: string | null; priced: number };
    config_drops: { value: number | null; first_run: boolean };
  };
  models: ModelTile[];
  hot_configs: HotConfig[];
  hot_count: number;
  hot_window: [string, string];
  changes: { date: string | null; previous: string | null; summary: ChangesSummary; models_new: ModelEvent[]; models_retired: ModelEvent[]; models_returned: ModelEvent[] };
  directory: {
    segments: Segment[]; engine_groups: string[]; plans: Record<PlanCode, PlanDef>; plan_footnotes: Record<string, string>;
    leasing_101: { fee_pct: number; term_months: number; residual_pct: number } | null;
    promos: Record<PromoKey, PromoDef>;
    scoring: {
      weights: { D: number; P: number; M: number; R: number }; momentum_cap_pct: number; momentum_new_car: number;
      promo_bonus: { pu: number; fe_or_p15: number; bo: number };
      hot: { hot_window_days: number; hot_drop_pct: number; hot_drop_pln: number; hot_new_score: number };
    };
    min_group: number; not_collected: string[];
  };
}

export interface RateSeries { priced: number[]; rate_min: Series; rate_median: Series }
export interface SeriesSet {
  offers: number[]; priced: number[]; special_min: Series; special_median: Series; special_max: Series;
  discount_pct_median: Series; rates: Record<string, RateSeries>; promo_counts: Record<PromoKey, Series>;
  net_added?: Series; net_removed?: Series; lfl_index?: Series; lowest_version_special?: Series;
  slider_counts?: Record<string, Series>; config_drops?: Series;
}
export interface Trends { dates: string[]; totals: SeriesSet; segments: Record<Segment, SeriesSet>; models: Record<string, SeriesSet> }

export interface ConfigHistory { offers: Series; priced: Series; special_min: Series; special_median: Series; special_max: Series }
export interface ModelFile {
  model: { name: string; slug: string; segment: Segment; order: number; status: 'active' | 'retired'; first_seen: string; last_seen: string | null; retired_on: string | null; empty_runs: number; engine_groups: string[]; engine_slots: Record<string, number>; possible_rename_of: string | null };
  dates: string[];
  timeline: SeriesSet;
  engines: Record<string, { slot: number; offers: number[]; priced: number[]; special_min: Series; special_median: Series }>;
  configurations: (ConfigInfo & { current: ConfigRow | null; history: ConfigHistory })[];
}

export interface DealsFile {
  date: string | null; hot_window: [string, string]; configs: ConfigRow[];
  rankings: { top_overall?: string[]; top_per_model?: Record<string, string[]>; top_per_segment?: Record<string, string[]> };
}

export interface ChangeConfig extends ConfigInfo { offers: number; priced: number }
export interface ChangesFile {
  date: string; previous: string | null;
  configs_new: (ChangeConfig & { special_median: number | null; score_best: number | null; reason: 'new_in_stock' | 'reached_minimum' })[];
  configs_gone: (ChangeConfig & { special_median: number | null; reason: 'none_left' | 'below_minimum' })[];
  price_drops: (ChangeConfig & { old: number; new: number; diff: number; pct: number; consecutive_drops?: number })[];
  price_rises: (ChangeConfig & { old: number; new: number; diff: number; pct: number })[];
  stock: { model: string; slug: string; offers_before: number; offers: number; net_added: number; net_removed: number }[];
  promo_changes: { model: string; slug: string; offers_before: number; offers: number; promo_changes: Partial<Record<PromoKey, { before: number; now: number }>> }[];
  summary: ChangesSummary;
  models_new: ModelEvent[]; models_retired: ModelEvent[]; models_returned: ModelEvent[];
}

export interface IndexEntry { date: string; status: 'ok' | 'suspect' | 'failed'; offers?: number; models?: number; configurations?: number; rules_version?: string; bundle_hash?: string | null }
export interface Manifest { latest: string | null; newest_snapshot: string | null; files: Record<string, string> }
export interface RowTable { columns: string[]; rows: unknown[][] }

// ---- private tree --------------------------------------------------------------------------------------------
export interface OfferRow {
  offer_id: string; model: string; slug: string; segment: Segment; engine: string | null; engine_group: string | null;
  code: string | null; model_year: string | null; production_year: string | null; catalog: number | null;
  special: number | null; discount: number | null; discount_pct: number | null; price_30d: number | null;
  promo_bits: number; rate: number | null; plan_code: PlanCode; initial_fee: number | null; term: number;
  identical: number; dealer_nr: string | null; dealer: string | null; config_key: string; config_change: number | null;
  lowest_ever: boolean; score: number | null; D: number | null; P: number | null; M: number | null; R: number | null;
  B: number | null; flags: string[]; hot: boolean;
}
export interface PrivateDeals { date: string | null; hot_window: [string, string]; columns: string[]; rows: unknown[][]; rankings: Record<string, unknown> }
export interface PrivateModelFile {
  model: { name: string; slug: string; segment: Segment; status: string }; dates: string[]; offers: RowTable;
  configurations: (ConfigInfo & { history: ConfigHistory })[];
}
export interface DealerSeries { nr: string; name: string | null; city: string | null; offers: number[]; discount_pct_median: Series; models_now: Record<string, number> }
export interface PrivateDealers { dates: string[]; dealers: DealerSeries[] }
export interface SnapshotOffer {
  offer_id: string; model: string; engine: string | null; engine_group: string | null; code: string | null;
  model_year: string | null; production_year: string | null; dealer_nr: string | null; dealer: string | null;
  catalog: number | null; special: number | null; price_30d: number | null; rate: number | null; promo_bits: number;
  plan_code: PlanCode; discount: number | null; discount_pct: number | null; config_key: string; version_key: string;
}
export interface SnapshotFile { date: string; offers: SnapshotOffer[] }
