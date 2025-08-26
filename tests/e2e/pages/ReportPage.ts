import { Page, Locator, expect } from '@playwright/test';

export class ReportPage {
  readonly page: Page;
  readonly scanResultsTitle: Locator;
  readonly progressSpinner: Locator;
  readonly totalDependenciesCard: Locator;
  readonly vulnerablePackagesCard: Locator;
  readonly cleanPackagesCard: Locator;
  readonly ecosystemsCard: Locator;
  readonly vulnerabilityTable: Locator;
  readonly noVulnerabilitiesMessage: Locator;
  readonly exportJsonButton: Locator;
  readonly exportCsvButton: Locator;
  readonly severityFilters: Locator;

  constructor(page: Page) {
    this.page = page;
    this.scanResultsTitle = page.getByRole('heading', { name: 'Scan Results' });
    this.progressSpinner = page.locator('.spinner-border');
    this.totalDependenciesCard = page.getByText('Total Dependencies');
    this.vulnerablePackagesCard = page.getByText('Vulnerable Packages');
    this.cleanPackagesCard = page.getByText('Clean Packages');
    this.ecosystemsCard = page.getByText('Ecosystems');
    this.vulnerabilityTable = page.locator('.card:has-text("Vulnerabilities Found")');
    this.noVulnerabilitiesMessage = page.getByText('No Vulnerabilities Found');
    this.exportJsonButton = page.getByRole('button', { name: /JSON/i });
    this.exportCsvButton = page.getByRole('button', { name: /CSV/i });
    this.severityFilters = page.locator('[role="group"][aria-label*="severity"]');
  }

  async waitForScanCompletion(timeoutMs: number = 120000) {
    // Wait for progress spinner to disappear
    await expect(this.progressSpinner).toBeHidden({ timeout: timeoutMs });
    
    // Wait for results to be visible
    await expect(this.scanResultsTitle).toBeVisible();
    await expect(this.totalDependenciesCard).toBeVisible();
  }

  async getTotalDependenciesCount(): Promise<number> {
    const card = this.totalDependenciesCard.locator('..');
    const countText = await card.textContent();
    const match = countText?.match(/(\d+)/);
    return match ? parseInt(match[1], 10) : 0;
  }

  async getVulnerablePackagesCount(): Promise<number> {
    const card = this.vulnerablePackagesCard.locator('..');
    const countText = await card.textContent();
    const match = countText?.match(/(\d+)/);
    return match ? parseInt(match[1], 10) : 0;
  }

  async verifyEcosystems(expectedEcosystems: string[]) {
    for (const ecosystem of expectedEcosystems) {
      await expect(this.ecosystemsCard.locator('..')).toContainText(ecosystem);
    }
  }

  async verifyNoVulnerabilities() {
    await expect(this.noVulnerabilitiesMessage).toBeVisible();
  }

  async verifyVulnerabilitiesFound() {
    await expect(this.vulnerabilityTable).toBeVisible();
  }

  async exportToJson() {
    const downloadPromise = this.page.waitForEvent('download');
    await this.exportJsonButton.click();
    return await downloadPromise;
  }

  async exportToCsv() {
    const downloadPromise = this.page.waitForEvent('download');
    await this.exportCsvButton.click();
    return await downloadPromise;
  }

  async filterBySeverity(severity: 'all' | 'critical' | 'high' | 'medium' | 'low') {
    const filterButton = this.severityFilters.getByRole('button', { name: new RegExp(severity, 'i') });
    await filterButton.click();
  }

  async getVulnerabilityDetails() {
    const vulnerabilityItems = this.page.locator('.card-body .border-bottom');
    const count = await vulnerabilityItems.count();
    const details = [];

    for (let i = 0; i < count; i++) {
      const item = vulnerabilityItems.nth(i);
      const packageName = await item.locator('.h5').first().textContent();
      const severity = await item.locator('[class*="severity"]').textContent();
      
      details.push({
        package: packageName?.split('@')[0] || '',
        severity: severity || ''
      });
    }

    return details;
  }
}