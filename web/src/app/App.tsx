// Router, providers and layout (spec 7.5): hash routing so deep links work on GitHub Pages.
import { Suspense, createElement, useEffect } from 'react';
import { HashRouter, NavLink, Route, Routes, matchPath, useLocation } from 'react-router-dom';
import { ThemeToggle } from '../components/common';
import { IS_PRIVATE } from '../lib/edition';
import { ThemeProvider } from '../lib/theme';
import { LatestProvider } from './latest';
import { ROUTES } from './routes';

function TitleAndFocus() {
  const { pathname } = useLocation();
  useEffect(() => {
    const r = ROUTES.find((x) => matchPath(x.path, pathname));
    const base = IS_PRIVATE ? 'Audilitics (private)' : 'Audilitics';
    document.title = r && r.path !== '/' ? `${r.title} – ${base}` : base;
  }, [pathname]);
  return null;
}

function Shell() {
  return (
    <div className="shell">
      <a className="skip" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById('main')?.focus(); }}>Skip to content</a>
      <header className="topbar">
        <NavLink to="/" className="brand" end>Audilitics{IS_PRIVATE && <span className="xs ink2" style={{ fontWeight: 400 }}> private</span>}</NavLink>
        <nav className="nav" aria-label="Main">
          {ROUTES.filter((r) => r.nav).map((r) => <NavLink key={r.path} to={r.path} end={r.path === '/'}>{r.nav}</NavLink>)}
        </nav>
        <ThemeToggle />
      </header>
      <main id="main" tabIndex={-1} style={{ outline: 'none' }}>
        <TitleAndFocus />
        <Suspense fallback={<div className="page" aria-busy="true"><p className="muted">Loading…</p></div>}>
          <Routes>
            {ROUTES.map((r) => <Route key={r.path} path={r.path} element={createElement(r.element)} />)}
            <Route path="*" element={<div className="page"><h1>Page not found</h1><p><NavLink to="/">Go to the overview</NavLink></p></div>} />
          </Routes>
        </Suspense>
      </main>
      <footer className="foot">
        Aggregates of offers published on gotowedoodbioru.audi.pl, collected every 14 days. The figures are not offers within the meaning of the Civil Code. Not affiliated with Audi or Volkswagen Group Polska.
        {IS_PRIVATE && ' Private build: offer-level data, for local use only.'}
      </footer>
    </div>
  );
}

export function App() {
  return (
    <ThemeProvider>
      <HashRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <LatestProvider>
          <Shell />
        </LatestProvider>
      </HashRouter>
    </ThemeProvider>
  );
}
