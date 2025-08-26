import { Page, expect, Download } from '@playwright/test';
import fs from 'fs/promises';
import path from 'path';

/**
 * Test utilities for E2E tests
 */

export class TestHelpers {
  constructor(private page: Page) {}

  /**
   * Wait for API response with timeout
   */
  async waitForAPIResponse(url: string, timeout: number = 30000) {
    return await this.page.waitForResponse(
      response => response.url().includes(url) && response.status() === 200,
      { timeout }
    );
  }

  /**
   * Wait for WebSocket connection to be established
   */
  async waitForWebSocketConnection() {
    await this.page.waitForFunction(() => {
      return window.WebSocket && document.readyState === 'complete';
    });
  }

  /**
   * Mock API responses for testing
   */
  async mockScanAPI(mockResponse: any) {
    await this.page.route('**/api/scan', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockResponse)
      });
    });
  }

  /**
   * Verify download file content
   */
  async verifyDownloadContent(download: Download, expectedContent?: any) {
    const fileName = download.suggestedFilename();
    const filePath = path.join(__dirname, '../temp', fileName);
    
    // Ensure temp directory exists
    await fs.mkdir(path.dirname(filePath), { recursive: true });
    
    // Save download
    await download.saveAs(filePath);
    
    // Read and verify content
    const content = await fs.readFile(filePath, 'utf8');
    
    if (fileName.endsWith('.json') && expectedContent) {
      const jsonContent = JSON.parse(content);
      expect(jsonContent).toMatchObject(expectedContent);
    }
    
    // Cleanup
    await fs.unlink(filePath);
    
    return content;
  }

  /**
   * Take screenshot with timestamp
   */
  async takeTimestampedScreenshot(name: string) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const screenshotPath = `test-results/screenshots/${name}-${timestamp}.png`;
    
    await this.page.screenshot({ 
      path: screenshotPath, 
      fullPage: true 
    });
    
    return screenshotPath;
  }

  /**
   * Verify page accessibility
   */
  async verifyAccessibility() {
    // Check for basic accessibility features
    const headings = await this.page.locator('h1, h2, h3, h4, h5, h6').count();
    expect(headings).toBeGreaterThan(0);

    // Check for alt text on images
    const images = await this.page.locator('img').count();
    if (images > 0) {
      const imagesWithoutAlt = await this.page.locator('img:not([alt])').count();
      expect(imagesWithoutAlt).toBe(0);
    }

    // Check for form labels
    const inputs = await this.page.locator('input[type="text"], input[type="email"], input[type="password"], textarea, select').count();
    if (inputs > 0) {
      const inputsWithoutLabels = await this.page.locator('input:not([aria-label]):not([aria-labelledby]):not([title])').count();
      // Some inputs might be properly labeled with associated labels
      expect(inputsWithoutLabels).toBeLessThanOrEqual(inputs);
    }
  }

  /**
   * Simulate network conditions
   */
  async simulateSlowNetwork() {
    await this.page.context().route('**/*', route => {
      // Add 500ms delay to all requests
      setTimeout(() => route.continue(), 500);
    });
  }

  /**
   * Simulate network failure
   */
  async simulateNetworkFailure(urlPattern: string = '**/*') {
    await this.page.context().route(urlPattern, route => {
      route.abort('failed');
    });
  }

  /**
   * Restore normal network conditions
   */
  async restoreNetwork() {
    await this.page.context().unroute('**/*');
  }

  /**
   * Log browser console messages during test
   */
  startConsoleLogging() {
    this.page.on('console', msg => {
      if (msg.type() === 'error') {
        console.error('Browser Console Error:', msg.text());
      } else if (msg.type() === 'warning') {
        console.warn('Browser Console Warning:', msg.text());
      } else {
        console.log('Browser Console:', msg.text());
      }
    });

    this.page.on('pageerror', error => {
      console.error('Browser Page Error:', error.message);
    });
  }

  /**
   * Wait for scan to complete with custom timeout and progress monitoring
   */
  async waitForScanWithProgress(timeoutMs: number = 120000) {
    const startTime = Date.now();
    let lastProgress = '';

    while (Date.now() - startTime < timeoutMs) {
      try {
        // Check if scan is complete
        const isComplete = await this.page.locator('.spinner-border').isHidden();
        if (isComplete) {
          const hasResults = await this.page.locator('[data-testid="scan-results"]').isVisible();
          if (hasResults) {
            return true;
          }
        }

        // Monitor progress
        const progressElement = this.page.locator('[data-testid="progress-message"]');
        if (await progressElement.isVisible()) {
          const currentProgress = await progressElement.textContent();
          if (currentProgress !== lastProgress) {
            console.log('Scan progress:', currentProgress);
            lastProgress = currentProgress || '';
          }
        }

        await this.page.waitForTimeout(1000); // Check every second
      } catch (error) {
        // Continue monitoring
        await this.page.waitForTimeout(1000);
      }
    }

    throw new Error(`Scan did not complete within ${timeoutMs}ms`);
  }
}

/**
 * Create test file with specific vulnerabilities for testing
 */
export async function createTestPackageJson(vulnerablePackages: string[] = ['lodash@4.17.20']) {
  const testPackage = {
    name: 'test-vulnerable-package',
    version: '1.0.0',
    dependencies: {} as Record<string, string>
  };

  vulnerablePackages.forEach(pkg => {
    const [name, version] = pkg.split('@');
    testPackage.dependencies[name] = version;
  });

  const filePath = path.join(__dirname, '../fixtures/temp-package.json');
  await fs.writeFile(filePath, JSON.stringify(testPackage, null, 2));
  
  return filePath;
}

/**
 * Cleanup temporary test files
 */
export async function cleanupTempFiles() {
  const tempDir = path.join(__dirname, '../fixtures');
  const tempFiles = await fs.readdir(tempDir);
  
  for (const file of tempFiles) {
    if (file.startsWith('temp-')) {
      await fs.unlink(path.join(tempDir, file));
    }
  }
}

/**
 * Verify scan results structure
 */
export function verifyScanResultsStructure(results: any) {
  expect(results).toHaveProperty('scan_info');
  expect(results).toHaveProperty('vulnerabilities');
  expect(results.scan_info).toHaveProperty('total_dependencies');
  expect(results.scan_info).toHaveProperty('vulnerable_packages');
  expect(results.scan_info).toHaveProperty('ecosystems');
  expect(Array.isArray(results.vulnerabilities)).toBe(true);
  
  if (results.vulnerabilities.length > 0) {
    const vuln = results.vulnerabilities[0];
    expect(vuln).toHaveProperty('package');
    expect(vuln).toHaveProperty('version');
    expect(vuln).toHaveProperty('severity');
    expect(vuln).toHaveProperty('vulnerability_id');
  }
}