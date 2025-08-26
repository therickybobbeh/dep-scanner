import { Page, Locator, expect } from '@playwright/test';

export class HomePage {
  readonly page: Page;
  readonly startScanningButton: Locator;
  readonly heroTitle: Locator;
  readonly featuresSection: Locator;

  constructor(page: Page) {
    this.page = page;
    this.startScanningButton = page.getByRole('link', { name: 'Start Scanning' });
    this.heroTitle = page.getByRole('heading', { name: 'Dependency Vulnerability Scanner' });
    this.featuresSection = page.getByRole('heading', { name: 'Features' });
  }

  async goto() {
    await this.page.goto('/');
  }

  async navigateToScan() {
    await this.startScanningButton.click();
  }

  async verifyPageContent() {
    await expect(this.heroTitle).toBeVisible();
    await expect(this.featuresSection).toBeVisible();
    await expect(this.startScanningButton).toBeVisible();
  }
}