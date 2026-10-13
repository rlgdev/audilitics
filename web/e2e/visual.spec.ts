import { test } from '@playwright/test';

// Visual record (spec 12.2): one full-page screenshot per public page per theme, from synthetic data, committed
// under e2e/screenshots/ so pull requests show the diff. Not an assertion: fonts render slightly differently per OS.
const PAGES: [string, string][] = [
  ['overview', '/#/'],
  ['model', '/#/model/q5'],
  ['deals', '/#/deals'],
  ['changes', '/#/changes'],
  ['about', '/#/about'],
];

for (const theme of ['light', 'dark'] as const) {
  for (const [name, url] of PAGES) {
    test(`screenshot ${name} ${theme}`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: theme, reducedMotion: 'reduce' });
      await page.goto(url);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(300);
      await page.screenshot({ path: `e2e/screenshots/${name}-${theme}.png`, fullPage: true });
    });
  }
}

test('screenshot overview phone', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/#/');
  await page.waitForLoadState('networkidle');
  await page.screenshot({ path: 'e2e/screenshots/overview-phone.png', fullPage: true });
});
