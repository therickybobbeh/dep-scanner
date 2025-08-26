import { Page, Locator, expect } from '@playwright/test';

export class ScanPage {
  readonly page: Page;
  readonly fileUploadInput: Locator;
  readonly fileUploadLabel: Locator;
  readonly uploadedFilesList: Locator;
  readonly includeDevDepsCheckbox: Locator;
  readonly enhancedResolutionCheckbox: Locator;
  readonly bypassCacheCheckbox: Locator;
  readonly startScanButton: Locator;
  readonly errorAlert: Locator;

  constructor(page: Page) {
    this.page = page;
    this.fileUploadInput = page.locator('#file-upload');
    this.fileUploadLabel = page.getByText('Drop files here or click to upload');
    this.uploadedFilesList = page.getByText('Uploaded Files');
    this.includeDevDepsCheckbox = page.getByLabel('Include development dependencies');
    this.enhancedResolutionCheckbox = page.getByLabel('Enhanced version resolution with transitive dependencies');
    this.bypassCacheCheckbox = page.getByLabel('Bypass version resolution cache');
    this.startScanButton = page.getByRole('button', { name: 'Start Vulnerability Scan' });
    this.errorAlert = page.locator('.alert-danger');
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
    enhancedResolution = true,
    bypassCache = false
  } = {}) {
    if (await this.includeDevDepsCheckbox.isChecked() !== includeDevDeps) {
      await this.includeDevDepsCheckbox.click();
    }
    if (await this.enhancedResolutionCheckbox.isChecked() !== enhancedResolution) {
      await this.enhancedResolutionCheckbox.click();
    }
    if (await this.bypassCacheCheckbox.isChecked() !== bypassCache) {
      await this.bypassCacheCheckbox.click();
    }
  }

  async startScan() {
    await this.startScanButton.click();
  }

  async verifyFileUploaded(fileName: string) {
    const fileItem = this.page.locator(`.list-group-item:has-text("${fileName}")`);
    await expect(fileItem).toBeVisible();
  }

  async verifyErrorMessage(message: string) {
    await expect(this.errorAlert).toContainText(message);
  }

  async waitForScanToStart() {
    // Wait for navigation to report page
    await this.page.waitForURL(/\/report\//);
  }
}