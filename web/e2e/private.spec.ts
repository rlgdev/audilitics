import { expect, test } from '@playwright/test';

// Private build on synthetic data (spec 12.1, private build): offers without identifier columns, the Car page with
// its configuration's history, dealers; still no link to audi.pl.

test('offers: every scored offer, no VIN or link column', async ({ page }) => {
  await page.goto('/#/offers');
  await expect(page.locator('.dt tbody tr').first()).toBeVisible();
  await expect(page.locator('.table-tools')).toContainText('112 offers'); // 116 offers, 4 without a special price
  const head = (await page.locator('.dt th').allTextContents()).join('|');
  expect(head).not.toMatch(/VIN|link/i);
  expect(head).toMatch(/Dealer/);
  expect(await page.locator('a[href*="audi.pl"]').count()).toBe(0);
});

test('an offer opens the Car page with its configuration history', async ({ page }) => {
  await page.goto('/#/offers');
  await page.locator('.dt tbody tr:not([aria-hidden])').first().click();
  await expect(page).toHaveURL(/#\/car\/\d{4}-\d{2}-\d{2}\/\d+/);
  await expect(page.getByText('Median special price of its configuration')).toBeVisible();
  await expect(page.locator('.chart svg')).toBeVisible();
  expect(await page.locator('a[href*="audi.pl"]').count()).toBe(0);
});

test('model page has an Offers tab in the private build', async ({ page }) => {
  await page.goto('/#/model/q5?tab=offers');
  await expect(page.getByRole('tab', { name: 'Offers' })).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('.dt tbody tr').first()).toBeVisible();
});

test('dealers page lists the invented dealers', async ({ page }) => {
  await page.goto('/#/dealers');
  await expect(page.locator('.dt tbody')).toContainText('Salon Alfa');
});
