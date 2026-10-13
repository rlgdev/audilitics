// latest.json is loaded once and shared: it carries the run metadata and every directory the UI needs.
import { createContext, useContext, type ReactNode } from 'react';
import { useData, type Loaded } from '../lib/data';
import type { Latest } from '../lib/types';

const LatestContext = createContext<Loaded<Latest>>({ data: null, error: null, loading: true });

export function LatestProvider({ children }: { children: ReactNode }) {
  const state = useData<Latest>('dashboard/latest.json');
  return <LatestContext.Provider value={state}>{children}</LatestContext.Provider>;
}

export function useLatest(): Latest | null {
  return useContext(LatestContext).data;
}

export function useLatestState(): Loaded<Latest> {
  return useContext(LatestContext);
}
