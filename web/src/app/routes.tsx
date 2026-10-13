// One routes module for both editions (spec 7.1, 7.5). The private routes are imported behind a build-time
// constant, so the public bundle contains no route, fetch or component for the private files.
import { lazy, type ComponentType, type LazyExoticComponent } from 'react';
import { IS_PRIVATE } from '../lib/edition';
import { Overview } from '../pages/Overview';

export interface AppRoute { path: string; element: ComponentType | LazyExoticComponent<ComponentType>; nav?: string; title: string }

const Model = lazy(() => import('../pages/Model').then((m) => ({ default: m.Model })));
const Deals = lazy(() => import('../pages/Deals').then((m) => ({ default: m.Deals })));
const Changes = lazy(() => import('../pages/Changes').then((m) => ({ default: m.Changes })));
const About = lazy(() => import('../pages/About').then((m) => ({ default: m.About })));

const PUBLIC: AppRoute[] = [
  { path: '/', element: Overview, nav: 'Overview', title: 'Overview' },
  { path: '/model/:slug', element: Model, title: 'Model' },
  { path: '/deals', element: Deals, nav: 'Best deals', title: 'Best deals' },
  { path: '/changes', element: Changes, nav: 'Changes', title: 'Changes' },
  { path: '/about', element: About, nav: 'About', title: 'About' },
];

const PRIVATE: AppRoute[] = IS_PRIVATE ? [
  { path: '/offers', element: lazy(() => import('../pages/private/Offers').then((m) => ({ default: m.Offers }))), nav: 'Offers', title: 'Offers' },
  { path: '/dealers', element: lazy(() => import('../pages/private/Dealers').then((m) => ({ default: m.Dealers }))), nav: 'Dealers', title: 'Dealers' },
  { path: '/car/:date/:n', element: lazy(() => import('../pages/private/Car').then((m) => ({ default: m.Car }))), title: 'Offer' },
] : [];

export const ROUTES: AppRoute[] = [...PUBLIC.slice(0, 4), ...PRIVATE, PUBLIC[4]];
