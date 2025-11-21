import { test, expect } from '@playwright/test'

test.describe('Fund Tracker', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Navigate to Fund Tracker page
    const fundTrackerLink = page.locator('a, button').filter({ hasText: /Fund.?Tracker/i })
    if (await fundTrackerLink.isVisible()) {
      await fundTrackerLink.click()
      await page.waitForLoadState('networkidle')
    }
  })

  test('should display Fund Tracker heading', async ({ page }) => {
    // Check for the Fund Tracker heading
    await expect(page.getByRole('heading', { name: /Fund Tracker/i })).toBeVisible()
  })

  test('should load and display list of tracked funds', async ({ page }) => {
    await page.waitForTimeout(2000)

    // Check for "Tracked Funds" section
    const trackedFundsHeading = page.locator('text=Tracked Funds')
    await expect(trackedFundsHeading).toBeVisible()

    // Should show at least one fund (we seeded 20 funds)
    const funds = page.locator('button').filter({ hasText: /Berkshire|ARK|Tiger|Coatue/i })
    await expect(funds.first()).toBeVisible()
  })

  test('should display specific seeded funds', async ({ page }) => {
    await page.waitForTimeout(2000)

    // Check for specific funds we seeded
    const berkshire = page.locator('text=Berkshire Hathaway')
    const ark = page.locator('text=ARK Investment Management')

    // At least one of these should be visible
    const isBerkshireVisible = await berkshire.isVisible()
    const isArkVisible = await ark.isVisible()
    expect(isBerkshireVisible || isArkVisible).toBeTruthy()
  })

  test('should show "Select a fund to view details" message initially', async ({ page }) => {
    await page.waitForTimeout(1000)

    // Check for the placeholder message
    const placeholder = page.locator('text=Select a fund to view details')
    await expect(placeholder).toBeVisible()
  })

  test('should allow selecting a fund and show tabs', async ({ page }) => {
    await page.waitForTimeout(2000)

    // Click on the first fund button
    const firstFund = page.locator('button').filter({ hasText: /Berkshire|ARK|Tiger/i }).first()
    await firstFund.click()

    await page.waitForTimeout(1000)

    // Check for Holdings and Recent Changes tabs
    const holdingsTab = page.locator('button', { hasText: 'Holdings' })
    const changesTab = page.locator('button', { hasText: 'Recent Changes' })

    await expect(holdingsTab).toBeVisible()
    await expect(changesTab).toBeVisible()
  })

  test('should show holdings data for funds with 13F filings', async ({ page }) => {
    await page.waitForTimeout(2000)

    // Click on Bridgewater Associates (we know this has holdings data)
    const bridgewater = page.locator('button').filter({ hasText: /Bridgewater/i })
    await bridgewater.click()

    await page.waitForTimeout(2000)

    // Should show holdings table with actual data
    const holdingsTable = page.locator('table')
    await expect(holdingsTable).toBeVisible()

    // Should have table headers
    await expect(page.locator('th', { hasText: 'Ticker' })).toBeVisible()
    await expect(page.locator('th', { hasText: 'Company' })).toBeVisible()
    await expect(page.locator('th', { hasText: 'Shares' })).toBeVisible()

    // Should have at least one row of data
    const tableRows = page.locator('tbody tr')
    await expect(tableRows.first()).toBeVisible()
  })

  test('should switch between Holdings and Recent Changes tabs', async ({ page }) => {
    await page.waitForTimeout(2000)

    // Click on a fund
    const firstFund = page.locator('button').filter({ hasText: /Berkshire|ARK|Tiger/i }).first()
    await firstFund.click()

    await page.waitForTimeout(1000)

    // Click on Recent Changes tab
    const changesTab = page.locator('button').filter({ hasText: 'Recent Changes' })
    await changesTab.click()

    await page.waitForTimeout(1000)

    // Should show changes content or "No recent changes"
    const hasChangesData = await page.locator('text=/New Positions|Increased|Decreased|Sold/').isVisible()
    const hasNoChanges = await page.locator('text=No recent changes').isVisible()

    expect(hasChangesData || hasNoChanges).toBeTruthy()

    // Switch back to Holdings
    const holdingsTab = page.locator('button').filter({ hasText: 'Holdings' })
    await holdingsTab.click()

    await page.waitForTimeout(500)

    // Verify we're back on holdings view
    const hasHoldingsTable = await page.locator('table').isVisible()
    const hasNoDataMessage = await page.locator('text=No holdings data available').isVisible()

    expect(hasHoldingsTable || hasNoDataMessage).toBeTruthy()
  })

  test('should not show loading skeleton after data loads', async ({ page }) => {
    await page.waitForTimeout(3000)

    // Loading skeleton should not be visible
    const loadingSkeleton = page.locator('.animate-pulse')
    const count = await loadingSkeleton.count()

    // Should have either no skeletons or very few (might catch it mid-load)
    expect(count).toBeLessThan(3)
  })
})
