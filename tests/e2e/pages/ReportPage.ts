import { Page, Locator, expect } from '@playwright/test';

export class ReportPage {
  readonly page: Page;
  readonly scanResultsTitle: Locator;
  readonly progressSpinner: Locator;
  readonly totalDependenciesCard: Locator;
  readonly vulnerablePackagesCard: Locator;
  readonly cleanPackagesCard: Locator;
  readonly scanTypeCard: Locator;
  readonly vulnerabilityTable: Locator;
  readonly noVulnerabilitiesMessage: Locator;
  readonly exportJsonButton: Locator;
  readonly exportCsvButton: Locator;
  readonly severityFilters: Locator;
  readonly tableViewTab: Locator;
  readonly cardsViewTab: Locator;
  readonly dependencyTable: Locator;

  constructor(page: Page) {
    this.page = page;
    this.scanResultsTitle = page.getByRole('heading', { name: 'Scan Results' });
    this.progressSpinner = page.locator('.spinner-border');
    this.totalDependenciesCard = page.getByText('Total Dependencies');
    this.vulnerablePackagesCard = page.getByText('Vulnerable Packages');
    this.cleanPackagesCard = page.getByText('Clean Packages');
    this.scanTypeCard = page.getByText('Scan Type');
    this.vulnerabilityTable = page.locator('.card:has-text("Vulnerabilities Found")');
    this.noVulnerabilitiesMessage = page.getByText('No Vulnerabilities Found');
    this.exportJsonButton = page.getByRole('button', { name: /Export JSON/i });
    this.exportCsvButton = page.getByRole('button', { name: /Export CSV/i });
    this.severityFilters = page.locator('[role="group"][aria-label*="severity"]');
    this.tableViewTab = page.getByRole('link', { name: 'Table View' });
    this.cardsViewTab = page.getByRole('link', { name: 'Cards View' });
    this.dependencyTable = page.locator('.dependency-table-container');
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
    // Ecosystems are now part of the scan summary, check scan type card
    for (const ecosystem of expectedEcosystems) {
      const pageContent = this.page.locator('body');
      await expect(pageContent).toContainText(ecosystem);
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
  
  async switchToTableView() {
    await this.tableViewTab.click();
    await expect(this.dependencyTable).toBeVisible();
  }
  
  async switchToCardsView() {
    await this.cardsViewTab.click();
    await expect(this.vulnerabilityTable).toBeVisible();
  }
  
  async verifyTableColumns() {
    await this.switchToTableView();
    
    // Verify table headers exist
    const table = this.dependencyTable.locator('table');
    await expect(table.locator('th:has-text("Package")')).toBeVisible();
    await expect(table.locator('th:has-text("Version")')).toBeVisible();
    await expect(table.locator('th:has-text("Severity")')).toBeVisible();
    await expect(table.locator('th:has-text("Score")')).toBeVisible();
    await expect(table.locator('th:has-text("Parent")')).toBeVisible();
    await expect(table.locator('th:has-text("Type")')).toBeVisible();
  }

  async getVulnerabilityDetails() {
    // Switch to table view for easier data extraction
    await this.switchToTableView();
    
    const tableRows = this.dependencyTable.locator('tbody tr');
    const count = await tableRows.count();
    const details = [];

    for (let i = 0; i < count; i++) {
      const row = tableRows.nth(i);
      const packageCell = row.locator('td').nth(1); // Package column
      const severityCell = row.locator('td').nth(3); // Severity column
      
      const packageName = await packageCell.locator('strong').textContent();
      const severityBadge = severityCell.locator('.badge');
      const severity = await severityBadge.textContent();
      
      details.push({
        package: packageName || '',
        severity: severity?.toLowerCase() || ''
      });
    }

    return details;
  }
}