import { defineConfig, devices } from '@playwright/test';

// Smoke and visual tests against `vite preview` of both builds on synthetic data only (spec 12.2).
// Build the dataset first: python -m collector --data-dir web/e2e/.data collect --fixture  (or `make e2e-data`)
const common = { viewport: { width: 1440, height: 1000 }, locale: 'pl-PL', timezoneId: 'Europe/Warsaw', acceptDownloads: true };

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  projects: [
    { name: 'public', testIgnore: /private\.spec\.ts/, use: { ...devices['Desktop Chrome'], ...common, baseURL: 'http://localhost:4174/' } },
    { name: 'private', testMatch: /private\.spec\.ts/, use: { ...devices['Desktop Chrome'], ...common, baseURL: 'http://localhost:4175/' } },
  ],
  webServer: [
    {
      command: 'npx vite build --outDir dist-e2e-public --emptyOutDir && npx vite preview --outDir dist-e2e-public --port 4174 --strictPort',
      url: 'http://localhost:4174/',
      env: { VITE_DATA_BASE: 'e2e/.data/public', VITE_BASE: '/', VITE_EDITION: 'public' },
      reuseExistingServer: false,
      timeout: 180_000,
    },
    {
      command: 'npx vite build --outDir dist-e2e-private --emptyOutDir && npx vite preview --outDir dist-e2e-private --port 4175 --strictPort',
      url: 'http://localhost:4175/',
      env: { VITE_DATA_BASE: 'e2e/.data', VITE_BASE: '/', VITE_EDITION: 'private' },
      reuseExistingServer: false,
      timeout: 180_000,
    },
  ],
});
