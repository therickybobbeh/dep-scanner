import { Page, Locator, expect } from '@playwright/test';

export class ScanPage {
  readonly page: Page;
  readonly fileUploadInput: Locator;
  readonly fileUploadLabel: Locator;
  readonly uploadedFilesList: Locator;
  readonly includeDevDepsCheckbox: Locator;
  readonly startScanButton: Locator;
  readonly errorAlert: Locator;
  readonly consistencyCheckButton: Locator;
  readonly consistencyAlert: Locator;
  readonly severityFilters: Locator;

  constructor(page: Page) {
    this.page = page;
    this.fileUploadInput = page.locator('input[type="file"]');
    this.fileUploadLabel = page.getByText('Choose Files');
    this.uploadedFilesList = page.locator('.list-group');
    this.includeDevDepsCheckbox = page.getByLabel('Include development dependencies');
    this.startScanButton = page.getByRole('button', { name: 'Start Vulnerability Scan' });
    this.errorAlert = page.locator('.alert-danger');
    this.consistencyCheckButton = page.getByRole('button', { name: 'Check Package Consistency' });
    this.consistencyAlert = page.locator('.alert-info');
    this.severityFilters = page.locator('.form-check-input');
  }

  async goto() {
    await this.page.goto('/scan');
  }

  async uploadFile(filePath: string) {
    await this.fileUploadInput.setInputFiles(filePath);
  }

  async uploadMultipleFiles(filePaths: string[]) {
    await this.fileUploadInput.setInputFiles(filePaths);
  }

  async removeUploadedFile(fileName: string) {
    const removeButton = this.page.locator(`text=${fileName}`).locator('..').getByRole('button');
    await removeButton.click();
  }

  async configureOptions({
    includeDevDeps = true,
    ignoreSeverities = []
  } = {}) {
    if (await this.includeDevDepsCheckbox.isChecked() !== includeDevDeps) {
      await this.includeDevDepsCheckbox.click();
    }
    
    // Handle severity filters
    for (const severity of ignoreSeverities) {
      const severityCheckbox = this.page.getByLabel(`Ignore ${severity} severity vulnerabilities`);
      if (await severityCheckbox.isVisible()) {
        await severityCheckbox.check();
      }
    }
  }

  async startScan() {
    await this.startScanButton.click();
  }

  async verifyFileUploaded(fileName: string) {
    const fileItem = this.page.locator(`.list-group-item:has-text("${fileName}")`);
    await expect(fileItem).toBeVisible();
    
    // Verify file badge shows correct type
    const fileBadge = fileItem.locator('.badge');
    await expect(fileBadge).toBeVisible();
  }
  
  async checkPackageConsistency() {
    await this.consistencyCheckButton.click();
    await expect(this.consistencyAlert).toBeVisible({ timeout: 10000 });
  }
  
  async verifyConsistencyResult(expectedResult: 'consistent' | 'inconsistent') {
    if (expectedResult === 'consistent') {
      await expect(this.consistencyAlert).toContainText('consistent');
    } else {
      await expect(this.consistencyAlert).toContainText('inconsistencies');
    }
  }

  async verifyErrorMessage(message: string) {
    await expect(this.errorAlert).toContainText(message);
  }

  async waitForScanToStart() {
    // Wait for navigation to report page
    await this.page.waitForURL(/\/report\//);
  }
}