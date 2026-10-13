import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';

// Public build on synthetic data (spec 12.1, 12.2): all public routes render; only aggregate files are requested;
// no link to audi.pl; filters -> URL -> reload; CSV export; drawer; keyboard path; 375 px.

const ROUTES = ['/#/', '/#/model/q5', '/#/deals', '/#/changes', '/#/about'];

async function errorsOf(page: Page) {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  return errors;
}

test('overview reads latest.json and trends.json only, from its own origin', async ({ page }) => {
  const errors = await errorsOf(page);
  const requests: string[] = [];
  page.on('request', (r) => requests.push(r.url()));
  await page.goto('/#/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.locator('.tile')).toHaveCount(6);
  await expect(page.locator('.hot').first()).toBeVisible();
  await page.waitForLoadState('networkidle');
  expect(requests.filter((u) => !u.startsWith('http://localhost:4174/'))).toEqual([]);
  const data = [...new Set(requests.filter((u) => u.includes('/data/')).map((u) => new URL(u).pathname.replace(/^.*\/data\//, '')))].sort();
  expect(data).toEqual(['dashboard/latest.json', 'dashboard/trends.json', 'manifest.json']);
  expect(errors).toEqual([]);
});

for (const route of ROUTES) {
  test(`route ${route}: renders, no private file, no link to audi.pl`, async ({ page }) => {
    const errors = await errorsOf(page);
    const requests: string[] = [];
    page.on('request', (r) => requests.push(r.url()));
    await page.goto(route);
    await expect(page.locator('h1')).toBeVisible();
    await expect(page.locator('h1')).not.toHaveText(/not found/i);
    await page.waitForLoadState('networkidle');
    expect(requests.filter((u) => /\/private\/|\.json\.gz|snapshots\/\d/.test(u))).toEqual([]);
    expect(await page.locator('a[href*="audi.pl"]').count()).toBe(0);
    expect(await page.content()).not.toMatch(/https?:\/\/[^"'\s]*audi\.pl/);
    expect(errors).toEqual([]);
  });
}

for (const route of ['/#/offers', '/#/dealers', '/#/car/2026-10-13/1']) {
  test(`private route ${route} is not found in the public build`, async ({ page }) => {
    await page.goto(route);
    await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible();
  });
}

test('hot deals: at most 8 cards; See all opens hot=1 with the same configuration first', async ({ page }) => {
  await page.goto('/#/');
  const cards = page.locator('.hot');
  await expect(cards.first()).toBeVisible();
  expect(await cards.count()).toBeLessThanOrEqual(8);
  const firstModel = (await cards.first().locator('.model').textContent())?.trim();
  await page.getByRole('link', { name: /See all/ }).click();
  await expect(page).toHaveURL(/#\/deals\?hot=1/);
  await expect(page.locator('.dt tbody tr:not([aria-hidden])').first()).toBeVisible();
  const first = await page.locator('.dt tbody tr:not([aria-hidden])').first().locator('td').nth(0).textContent();
  expect(first?.trim()).toBe(firstModel);
});

test('hot card opens the model page with its configuration drawer', async ({ page }) => {
  await page.goto('/#/');
  await page.locator('.hot .model').first().click();
  await expect(page).toHaveURL(/#\/model\/[a-z0-9-]+\?config=[0-9a-f]{16}/);
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('model page: median and band, one tooltip with offers, median, min and max; index starts at 100', async ({ page }) => {
  await page.goto('/#/model/q5');
  const chart = page.locator('.chart.tall').first();
  await expect(chart.locator('svg')).toBeVisible();
  const box = (await chart.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.4, box.y + box.height / 2);
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height / 2, { steps: 5 });
  const tip = page.locator('div').filter({ hasText: /median special price/ }).filter({ hasText: /max/ }).last();
  await expect(tip).toContainText('min');
  await page.getByRole('button', { name: 'Show data' }).nth(1).click();
  await expect(page.locator('table').filter({ hasText: 'Index' }).locator('tbody tr').first()).toContainText('100');
  await expect(page.locator('table:has(caption) tbody tr').first()).toBeVisible();
  const offers = await page.locator('table:has(caption) tbody tr:not([aria-hidden])').evaluateAll((rows) => rows.map((r) => Number((r.children[4]?.textContent ?? '0').replace(/\D/g, ''))));
  expect(offers.length).toBeGreaterThan(0);
  for (const o of offers) expect(o).toBeGreaterThanOrEqual(3);
});

test('configuration row opens the drawer', async ({ page }) => {
  await page.goto('/#/deals');
  await page.locator('.dt tbody tr:not([aria-hidden])').first().click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog')).toContainText('median special price');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});

test('filters live in the URL and survive a reload', async ({ page }) => {
  await page.goto('/#/deals?segment=q&promo=l101');
  await expect(page.locator('.dt tbody tr').first()).toBeVisible();
  await page.locator('th button', { hasText: 'Special price (median)' }).click();
  await expect(page.locator('th', { hasText: 'Special price (median)' })).toHaveAttribute('aria-sort', 'ascending');
  const url = page.url();
  const first = await page.locator('.dt tbody tr:not([aria-hidden])').first().textContent();
  const p2 = await page.context().newPage();
  await p2.goto(url);
  await expect(p2.getByRole('tab', { name: 'Q', exact: true })).toHaveAttribute('aria-selected', 'true');
  await expect(p2.locator('.filter.on summary', { hasText: 'Promo' })).toBeVisible();
  await expect(p2.locator('.dt tbody tr').first()).toBeVisible();
  expect(await p2.locator('.dt tbody tr:not([aria-hidden])').first().textContent()).toBe(first);
});

test('top 3 per model gives at most 3 rows per model', async ({ page }) => {
  await page.goto('/#/deals?top3=1');
  await expect(page.locator('.dt tbody tr').first()).toBeVisible();
  const models = await page.locator('.dt tbody tr:not([aria-hidden])').evaluateAll((rows) => rows.map((r) => r.children[0]?.textContent ?? ''));
  const counts = new Map<string, number>();
  for (const m of models) counts.set(m, (counts.get(m) ?? 0) + 1);
  for (const [, c] of counts) expect(c).toBeLessThanOrEqual(3);
});

test('CSV export of a configuration table: visible rows and columns, numbers unformatted', async ({ page }) => {
  await page.goto('/#/model/q5');
  await expect(page.locator('.dt tbody tr').first()).toBeVisible();
  const rows = await page.locator('.dt tbody tr:not([aria-hidden])').count();
  const headers = await page.locator('.dt th').allTextContents();
  const [dl] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Export CSV' }).click()]);
  const text = fs.readFileSync((await dl.path())!, 'utf8').replace(/^\uFEFF/, '');
  const lines = text.trim().split('\n');
  expect(lines.length).toBe(rows + 1);
  expect(lines[0].split(',').length).toBe(headers.length);
  const col = lines[0].split(',').indexOf('Special price (median)');
  for (const line of lines.slice(1)) expect(line.split(',')[col]).toMatch(/^\d+(\.\d+)?$/); // numbers unformatted
});

test('changes: drops with old, new, difference and %; gone configurations listed', async ({ page }) => {
  await page.goto('/#/changes');
  await expect(page.getByRole('tab', { name: /Price drops/ })).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('.dt th').first()).toBeVisible();
  const head = await page.locator('.dt th').allTextContents();
  expect(head.join('|')).toMatch(/Previous median.*New median.*Difference.*Change %/);
  await page.getByRole('tab', { name: /Gone configurations/ }).click();
  await expect(page.locator('.dt tbody')).toContainText('GUBAZY');
  await page.getByRole('tab', { name: /Stock by model/ }).click();
  await expect(page.locator('.dt th', { hasText: 'Net added' })).toBeVisible();
});

test('keyboard path: filters, model tile, hot card, theme toggle reachable with focus ring', async ({ page }) => {
  await page.goto('/#/');
  await expect(page.locator('.hot').first()).toBeVisible();
  const seen = new Set<string>();
  for (let i = 0; i < 45; i++) {
    await page.keyboard.press('Tab');
    seen.add(await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el) return '';
      return `${el.tagName}:${(el.textContent ?? '').trim().slice(0, 20)}:${getComputedStyle(el).outlineStyle}`;
    }));
  }
  const all = [...seen].join('\n');
  expect(all).toMatch(/SUMMARY:Period/);
  expect(all).toMatch(/BUTTON:Dark/);
  expect(all).toMatch(/A:(Q5|Q7|A3|RS 3|Q4|A6)/);
  expect([...seen].filter((s) => s.endsWith(':none') && !s.startsWith('BODY:'))).toEqual([]);
});

test('theme toggle switches to the dark token set', async ({ page }) => {
  await page.goto('/#/');
  await page.getByRole('button', { name: 'Dark' }).click();
  expect(await page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe('rgb(13, 13, 13)');
});

test('375 px: no horizontal page scroll on any public page', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  for (const route of ROUTES) {
    await page.goto(route);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500); // charts settle to their container width
    expect(await page.evaluate(() => document.documentElement.scrollWidth), route).toBeLessThanOrEqual(375);
  }
});
