import { test, expect } from '@playwright/test';

test.describe('MOSO AI Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('loads with all three panels', async ({ page }) => {
    await expect(page.locator('text=MOSO')).toBeVisible();
    await expect(page.locator('text=LOG')).toBeVisible();
    await expect(page.locator('text=AURA')).toBeVisible();
    await expect(page.locator('text=EXPLAINER')).toBeVisible();
  });

  test('top nav shows system stats', async ({ page }) => {
    await expect(page.locator('text=LIVE')).toBeVisible();
    await expect(page.locator('text=CPU')).toBeVisible();
    await expect(page.locator('text=GPU')).toBeVisible();
    await expect(page.locator('text=RAM')).toBeVisible();
  });

  test('status bar shows all indicators', async ({ page }) => {
    await expect(page.locator('text=Memory Synced')).toBeVisible();
    await expect(page.locator('text=Local Mode')).toBeVisible();
    await expect(page.locator('text=Offline Ready')).toBeVisible();
    await expect(page.locator('text=End-to-End Encrypted')).toBeVisible();
  });

  test('log panel has search input', async ({ page }) => {
    const search = page.locator('input[placeholder="Search"]');
    await expect(search).toBeVisible();
  });

  test('log panel shows date groups', async ({ page }) => {
    await expect(page.locator('text=Today')).toBeVisible();
    await expect(page.locator('text=Yesterday')).toBeVisible();
  });

  test('log panel has filter buttons', async ({ page }) => {
    await expect(page.locator('button:has-text("Flutter")')).toBeVisible();
    await expect(page.locator('button:has-text("AI")')).toBeVisible();
    await expect(page.locator('button:has-text("Code")')).toBeVisible();
  });

  test('aura panel has AI orb', async ({ page }) => {
    await expect(page.locator('text=Listening...')).toBeVisible();
  });

  test('aura panel has message input', async ({ page }) => {
    const input = page.locator('input[placeholder="Type a message..."]');
    await expect(input).toBeVisible();
  });

  test('explainer panel shows empty state', async ({ page }) => {
    await expect(page.locator('text=Nothing to explain yet')).toBeVisible();
  });

  test('explainer panel has tabs', async ({ page }) => {
    await expect(page.locator('button:has-text("Flowchart")')).toBeVisible();
    await expect(page.locator('button:has-text("Table")')).toBeVisible();
    await expect(page.locator('button:has-text("Graph")')).toBeVisible();
    await expect(page.locator('button:has-text("Code")')).toBeVisible();
  });

  test('can type and send a message', async ({ page }) => {
    const input = page.locator('input[placeholder="Type a message..."]');
    await input.fill('Hello MOSO');
    await input.press('Enter');
    await expect(page.locator('text=Hello MOSO')).toBeVisible();
  });

  test('can search logs', async ({ page }) => {
    const search = page.locator('input[placeholder="Search"]');
    await search.fill('Flutter');
    await expect(page.locator('text=Flutter UI')).toBeVisible();
  });

  test('can filter logs', async ({ page }) => {
    await page.locator('button:has-text("AI")').first().click();
    // AI filter should be active
    const aiBtn = page.locator('button:has-text("AI")').first();
    await expect(aiBtn).toHaveClass(/bg-moso-purple/);
  });

  test('can select a log entry', async ({ page }) => {
    await page.locator('text=Flutter UI').first().click();
    await expect(page.locator('text=Analysis of')).toBeVisible();
  });

  test('can switch explainer tabs', async ({ page }) => {
    await page.locator('button:has-text("Table")').click();
    await expect(page.locator('th:has-text("Component")')).toBeVisible();
  });

  test('activity feed is visible', async ({ page }) => {
    await expect(page.locator('text=Activity Feed')).toBeVisible();
    await expect(page.locator('text=Thinking...')).toBeVisible();
    await expect(page.locator('text=Agent Finished')).toBeVisible();
  });
});
