# ADR-0003: TanStack Table and TanStack Virtual for car tables

Status: Accepted, 2026-10-13.

Context: Car lists hold up to about 5,000 rows and need sorting, a column chooser, a sticky header, CSV export of the current view and 60 fps scrolling (spec 7.3, spec 11).

Decision: Use headless TanStack Table (`@tanstack/react-table`) with TanStack Virtual (`@tanstack/react-virtual`) inside one wrapper, `web/src/components/DataTable.tsx`, used by the Model, Deals, Changes and Dealers pages.

Consequences: Markup and styling stay ours, so tables follow the design tokens. Only visible rows are rendered. The collector stores car tables as `columns` plus `rows` arrays to keep the JSON small; `toRows` in `web/src/lib/data.ts` maps them to objects.
