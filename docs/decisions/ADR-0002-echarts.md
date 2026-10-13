# ADR-0002: Apache ECharts for charts

Status: Accepted, 2026-10-13.

Context: The dashboard needs line charts with crosshair tooltips, min-max bands, bars and sparklines, themed from one set of tokens in light and dark mode, with tooltips on keyboard focus (spec 7.4, spec 8.3).

Decision: Use Apache ECharts 5 (`echarts` 5.5.1) behind one wrapper, `web/src/charts/EChart.tsx`, and one theme built from `tokens.css` at run time, `web/src/charts/theme.ts`.

Consequences: Every chart shares one theme, so colours, gridlines and tooltips stay consistent and follow the theme toggle. The chart rules of spec 8.3 are applied in our option builders, not by the library. ECharts counts against the 350 kB first-load JavaScript budget (spec 11).
