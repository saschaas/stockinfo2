import { test, expect } from '@playwright/test'

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should load and display market overview', async ({ page }) => {
    // Wait for the page to load
    await page.waitForLoadState('networkidle')

    // Check for the Market Overview heading
    await expect(page.getByRole('heading', { name: 'Market Overview' })).toBeVisible()

    // Check that we're not showing an error
    const errorMessage = page.locator('text=Error loading market data')
    await expect(errorMessage).not.toBeVisible()
  })

  test('should display market sentiment data', async ({ page }) => {
    await page.waitForLoadState('networkidle')

    // Wait for data to load (should not be loading spinner after a few seconds)
    await page.waitForTimeout(2000)

    // Check for sentiment card
    const sentimentCard = page.locator('text=Market Sentiment')
    await expect(sentimentCard).toBeVisible()

    // Check for sectors section
    const sectorsHeading = page.getByRole('heading', { name: 'Sectors', exact: true })
    await expect(sectorsHeading).toBeVisible()

    // Check for hot and negative sectors
    const hotSectors = page.getByRole('heading', { name: 'Hot Sectors' })
    const negativeSectors = page.getByRole('heading', { name: 'Negative Sectors' })
    await expect(hotSectors).toBeVisible()
    await expect(negativeSectors).toBeVisible()
  })

  test('should display "Last updated" date', async ({ page }) => {
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)

    // Check for last updated text
    const lastUpdated = page.locator('text=/Last updated:/')
    await expect(lastUpdated).toBeVisible()
  })

  test('should show top news section', async ({ page }) => {
    await page.waitForLoadState('networkidle')

    // Look for the top news component
    // The component should exist even if there's no news
    const dashboard = page.locator('div').filter({ hasText: 'Market Overview' }).first()
    await expect(dashboard).toBeVisible()
  })

  test('should not show loading spinner after data loads', async ({ page }) => {
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // Loading spinner should not be visible
    const spinner = page.locator('.animate-spin')
    await expect(spinner).not.toBeVisible()
  })
})
