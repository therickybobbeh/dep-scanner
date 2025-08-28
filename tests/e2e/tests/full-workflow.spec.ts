import { test, expect } from '@playwright/test';
import { HomePage } from '../pages/HomePage';
import { ScanPage } from '../pages/ScanPage';
import { ReportPage } from '../pages/ReportPage';
import path from 'path';

test.describe('Complete User Workflows', () => {
  let homePage: HomePage;
  let scanPage: ScanPage;
  let reportPage: ReportPage;

  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    scanPage = new ScanPage(page);
    reportPage = new ReportPage(page);
  });

  test('complete vulnerability scanning workflow', async ({ page }) => {
    // Step 1: Start from homepage
    await homePage.goto();
    await homePage.verifyPageContent();

    // Step 2: Navigate to scan page
    await homePage.navigateToScan();

    // Step 3: Upload a dependency file
    const packageJsonPath = path.join(__dirname, '../fixtures/package.json');
    await scanPage.uploadFile(packageJsonPath);
    await scanPage.verifyFileUploaded('package.json');

    // Step 4: Configure scan options
    await scanPage.configureOptions({
      includeDevDeps: true,
      ignoreSeverities: [] // Empty array means don't ignore any severities
    });

    // Step 5: Start the scan
    await scanPage.startScan();
    await scanPage.waitForScanToStart();

    // Step 6: Wait for scan completion and verify results
    await reportPage.waitForScanCompletion();

    const dependencyCount = await reportPage.getTotalDependenciesCount();
    expect(dependencyCount).toBeGreaterThan(0);

    // Step 7: Test vulnerability filtering (if vulnerabilities exist)
    const vulnerableCount = await reportPage.getVulnerablePackagesCount();
    
    if (vulnerableCount > 0) {
      await reportPage.verifyVulnerabilitiesFound();
      
      // Test severity filtering
      await reportPage.filterBySeverity('high');
      await reportPage.filterBySeverity('all');
    } else {
      await reportPage.verifyNoVulnerabilities();
    }

    // Step 8: Test table view functionality
    await reportPage.verifyTableColumns();
    
    // Step 9: Test export functionality
    const jsonDownload = await reportPage.exportToJson();
    expect(jsonDownload.suggestedFilename()).toMatch(/depscan_report_.*\.json$/);

    const csvDownload = await reportPage.exportToCsv();
    expect(csvDownload.suggestedFilename()).toMatch(/depscan_report_.*\.csv$/);
  });

  test('error handling workflow', async ({ page }) => {
    await scanPage.goto();

    // Test 1: Try to scan without uploading files
    await expect(scanPage.startScanButton).toBeDisabled();

    // Test 2: Upload a file, then remove it, then verify button is disabled
    const packageJsonPath = path.join(__dirname, '../fixtures/package.json');
    await scanPage.uploadFile(packageJsonPath);
    await scanPage.verifyFileUploaded('package.json');
    await expect(scanPage.startScanButton).toBeEnabled();

    await scanPage.removeUploadedFile('package.json');
    await expect(scanPage.startScanButton).toBeDisabled();
  });

  test('multi-ecosystem scanning workflow', async ({ page }) => {
    await scanPage.goto();

    // Upload files from different ecosystems
    const filePaths = [
      path.join(__dirname, '../fixtures/package.json'),
      path.join(__dirname, '../fixtures/requirements.txt')
    ];

    await scanPage.uploadMultipleFiles(filePaths);
    await scanPage.verifyFileUploaded('package.json');
    await scanPage.verifyFileUploaded('requirements.txt');

    // Configure for comprehensive scan
    await scanPage.configureOptions({
      includeDevDeps: true,
      ignoreSeverities: []
    });

    await scanPage.startScan();
    await scanPage.waitForScanToStart();

    // Wait for completion with extended timeout for multi-ecosystem scan
    await reportPage.waitForScanCompletion(180000);

    // Verify both ecosystems are detected
    await reportPage.verifyEcosystems(['JavaScript', 'Python']);

    // Verify we have dependencies from both ecosystems
    const totalDeps = await reportPage.getTotalDependenciesCount();
    expect(totalDeps).toBeGreaterThanOrEqual(8); // At least 3 JS + 5 Python = 8 direct deps
  });

  test('WebSocket progress updates workflow', async ({ page }) => {
    await scanPage.goto();

    // Upload a file that will trigger progress updates
    const packageJsonPath = path.join(__dirname, '../fixtures/package.json');
    await scanPage.uploadFile(packageJsonPath);

    await scanPage.configureOptions({
      includeDevDeps: true // Include dev deps for more comprehensive scan
    });

    await scanPage.startScan();
    await scanPage.waitForScanToStart();

    // Verify that we see progress indicators
    await expect(reportPage.progressSpinner).toBeVisible();

    // Wait for scan to start processing
    await page.waitForTimeout(2000);

    // Verify progress updates are happening (spinner should still be visible during processing)
    await expect(reportPage.progressSpinner).toBeVisible();

    // Wait for completion
    await reportPage.waitForScanCompletion();

    // Verify final state
    await expect(reportPage.progressSpinner).toBeHidden();
    await expect(reportPage.scanResultsTitle).toBeVisible();
  });

  test('responsive design workflow', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await homePage.goto();
    await homePage.verifyPageContent();

    await homePage.navigateToScan();

    // Upload and scan on mobile
    const packageJsonPath = path.join(__dirname, '../fixtures/package.json');
    await scanPage.uploadFile(packageJsonPath);
    await scanPage.verifyFileUploaded('package.json');

    await scanPage.startScan();
    await scanPage.waitForScanToStart();
    await reportPage.waitForScanCompletion();

    // Verify results display correctly on mobile
    const dependencyCount = await reportPage.getTotalDependenciesCount();
    expect(dependencyCount).toBeGreaterThan(0);

    // Reset to desktop viewport for other tests
    await page.setViewportSize({ width: 1280, height: 720 });
  });

  test('navigation and back button workflow', async ({ page }) => {
    // Start from home page
    await homePage.goto();
    
    // Navigate to scan
    await homePage.navigateToScan();
    expect(page.url()).toContain('/scan');

    // Upload file and start scan
    const packageJsonPath = path.join(__dirname, '../fixtures/package.json');
    await scanPage.uploadFile(packageJsonPath);
    await scanPage.startScan();
    await scanPage.waitForScanToStart();

    // Should be on report page
    expect(page.url()).toMatch(/\/report\//);

    // Use browser back button
    await page.goBack();
    expect(page.url()).toContain('/scan');

    // Navigate back to report
    await page.goForward();
    expect(page.url()).toMatch(/\/report\//);

    // Wait for completion
    await reportPage.waitForScanCompletion();
  });
});