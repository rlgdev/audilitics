/// <reference types="vitest" />
import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';
import type { IncomingMessage, ServerResponse } from 'node:http';

// One variable controls the site base (spec 10.1): VITE_BASE=/audilitics/ on GitHub Pages, "/" for a custom domain.
const base = process.env.VITE_BASE ?? '/';
// Local data directory served at <base>data/ in dev and preview (spec 10.3: VITE_DATA_BASE=../data).
const dataDir = path.resolve(__dirname, process.env.VITE_DATA_BASE ?? '../data');

function serveData(): Plugin {
  const handler = (req: IncomingMessage, res: ServerResponse, next: () => void) => {
    const prefix = base.replace(/\/$/, '') + '/data/';
    if (!req.url || !req.url.startsWith(prefix)) return next();
    const rel = decodeURIComponent(req.url.slice(prefix.length).split('?')[0]);
    const file = path.join(dataDir, rel);
    if (!file.startsWith(dataDir) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) return next();
    const type = file.endsWith('.json') ? 'application/json' : file.endsWith('.csv') ? 'text/csv' : file.endsWith('.md') ? 'text/markdown; charset=utf-8' : 'application/octet-stream';
    res.setHeader('Content-Type', type);
    res.end(fs.readFileSync(file));
  };
  return {
    name: 'audilitics-serve-data',
    configureServer(server) { server.middlewares.use(handler); },
    configurePreviewServer(server) { server.middlewares.use(handler); },
  };
}

export default defineConfig({
  base,
  plugins: [react(), serveData()],
  build: {
    target: 'es2022',
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ['echarts/core', 'echarts/charts', 'echarts/components', 'echarts/renderers'],
          table: ['@tanstack/react-table', '@tanstack/react-virtual'],
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
