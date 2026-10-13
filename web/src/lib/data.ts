// Data loading (spec 7.5, 10.2). The public build fetches only <base>/data/... (the public tree). The private build
// reads one private checkout served at <base>/data/: public files from public/, private files from private/,
// snapshots from snapshots/. Files are cached in memory per snapshot date; manifest.json busts the cache.
import { useEffect, useRef, useState } from 'react';
import { IS_PRIVATE } from './edition';
import type { Manifest, RowTable } from './types';

export type Tree = 'public' | 'private' | 'snapshots';

const BASE = `${import.meta.env.BASE_URL}data/`;
const cache = new Map<string, Promise<unknown>>();
let manifestDate: string | null | undefined;
let manifestPromise: Promise<Manifest> | null = null;

export function dataUrl(path: string, tree: Tree = 'public'): string {
  if (!IS_PRIVATE) return BASE + path;
  return BASE + (tree === 'public' ? 'public/' : tree === 'private' ? 'private/' : 'snapshots/') + path;
}

async function fetchJson<T>(url: string, gz: boolean): Promise<T> {
  const r = await fetch(url, { cache: 'no-cache' });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  if (!gz || !IS_PRIVATE) return (await r.json()) as T;
  // Snapshots are read only by the private Car page; the public build drops this branch.
  const stream = r.body!.pipeThrough(new DecompressionStream('gzip'));
  return JSON.parse(await new Response(stream).text()) as T;
}

export function loadManifest(force = false): Promise<Manifest> {
  if (!manifestPromise || force) {
    manifestPromise = fetchJson<Manifest>(dataUrl('manifest.json'), false).then((m) => {
      if (manifestDate !== undefined && manifestDate !== m.latest) cache.clear();
      manifestDate = m.latest;
      return m;
    });
  }
  return manifestPromise;
}

export async function load<T>(path: string, tree: Tree = 'public'): Promise<T> {
  const m = await loadManifest();
  const key = `${m.latest}:${tree}:${path}`;
  let p = cache.get(key);
  if (!p) {
    const v = tree === 'public' && m.files[path] ? `?v=${m.files[path]}` : '';
    p = fetchJson<T>(dataUrl(path, tree) + v, path.endsWith('.gz')).catch((e: Error) => {
      cache.delete(key);
      throw new Error(`${path}: ${e.message}`);
    });
    cache.set(key, p);
  }
  return p as Promise<T>;
}

export interface Loaded<T> { data: T | null; error: Error | null; loading: boolean }

/** Fetch a data file; while a new path loads the previous data stays (rendered at reduced opacity). */
export function useData<T>(path: string | null, tree: Tree = 'public'): Loaded<T> {
  const [state, setState] = useState<Loaded<T>>({ data: null, error: null, loading: !!path });
  const current = useRef(path);
  useEffect(() => {
    current.current = path;
    if (!path) {
      setState({ data: null, error: null, loading: false });
      return;
    }
    setState((s) => ({ ...s, loading: true, error: null }));
    load<T>(path, tree).then(
      (data) => current.current === path && setState({ data, error: null, loading: false }),
      (error: Error) => current.current === path && setState({ data: null, error, loading: false }),
    );
  }, [path, tree]);
  return state;
}

/** Column table -> row objects. */
export function toRows<T>(t: RowTable | null | undefined): T[] {
  if (!t) return [];
  const cols = t.columns;
  return t.rows.map((r) => {
    const o: Record<string, unknown> = {};
    for (let i = 0; i < cols.length; i++) o[cols[i]] = r[i];
    return o as T;
  });
}
