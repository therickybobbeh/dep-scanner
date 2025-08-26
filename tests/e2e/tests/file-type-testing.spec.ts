import { test, expect } from '@playwright/test';
import { HomePage } from '../pages/HomePage';
import { ScanPage } from '../pages/ScanPage';
import { ReportPage } from '../pages/ReportPage';
import path from 'path';

// Test data for different file types
const testFiles = [
  {
    name: 'package.json',
    path: path.join(__dirname, '../fixtures/package.json'),
    expectedEcosystem: 'JavaScript',
    expectTransitive: true,
    minDependencies: 3, // At least the direct dependencies
  },
  {
    name: 'package-lock.json', 
    path: path.join(__dirname, '../fixtures/package-lock.json'),
    expectedEcosystem: 'JavaScript',
    expectTransitive: true,
    minDependencies: 3, // Should include transitive dependencies
  },
  {
    name: 'requirements.txt',
    path: path.join(__dirname, '../fixtures/requirements.txt'),
    expectedEcosystem: 'Python',
    expectTransitive: false,
    minDependencies: 5, // Direct dependencies only
  }
];

test.describe('File Type Testing', () => {
  let homePage: HomePage;
  let scanPage: ScanPage;
  let reportPage: ReportPage;

  test.beforeEach(async ({ page }) => {
    homePage = new HomePage(page);
    scanPage = new ScanPage(page);
    reportPage = new ReportPage(page);
  });

  for (const fileData of testFiles) {
    test(`should successfully scan ${fileData.name}`, async ({ page }) => {
      // Navigate to scan page
      await scanPage.goto();

      // Upload the test file
      await scanPage.uploadFile(fileData.path);
      await scanPage.verifyFileUploaded(fileData.name);

      // Configure scan options
      await scanPage.configureOptions({
        includeDevDeps: true,
        enhancedResolution: fileData.expectTransitive,
        bypassCache: false
      });

      // Start the scan
      await scanPage.startScan();
      await scanPage.waitForScanToStart();

      // Wait for scan completion
      await reportPage.waitForScanCompletion();

      // Verify results
      const dependencyCount = await reportPage.getTotalDependenciesCount();
      expect(dependencyCount).toBeGreaterThanOrEqual(fileData.minDependencies);

      // Verify expected ecosystem
      await reportPage.verifyEcosystems([fileData.expectedEcosystem]);

      // Test export functionality
      const jsonDownload = await reportPage.exportToJson();
      expect(jsonDownload.suggestedFilename()).toMatch(/\.json$/);

      const csvDownload = await reportPage.exportToCsv();
      expect(csvDownload.suggestedFilename()).toMatch(/\.csv$/);
    });
  }

  test('should handle multiple file upload correctly', async ({ page }) => {
    await scanPage.goto();

    // Upload multiple files
    const filePaths = [
      path.join(__dirname, '../fixtures/package.json'),
      path.join(__dirname, '../fixtures/requirements.txt')
    ];
    
    await scanPage.uploadMultipleFiles(filePaths);
    
    // Verify both files are uploaded
    await scanPage.verifyFileUploaded('package.json');
    await scanPage.verifyFileUploaded('requirements.txt');

    // Start scan
    await scanPage.startScan();
    await scanPage.waitForScanToStart();

    // Wait for completion
    await reportPage.waitForScanCompletion();

    // Should detect both ecosystems
    await reportPage.verifyEcosystems(['JavaScript', 'Python']);
  });

  test('should show error for empty upload', async ({ page }) => {
    await scanPage.goto();

    // Try to start scan without uploading files
    await scanPage.startScan();

    // Should show error message
    await scanPage.verifyErrorMessage('Please upload at least one dependency file');
  });

  test('should allow file removal', async ({ page }) => {
    await scanPage.goto();

    // Upload a file
    await scanPage.uploadFile(path.join(__dirname, '../fixtures/package.json'));
    await scanPage.verifyFileUploaded('package.json');

    // Remove the file
    await scanPage.removeUploadedFile('package.json');

    // File should be gone, scan button should be disabled
    await expect(scanPage.startScanButton).toBeDisabled();
  });

  test('should handle transitive vs direct dependencies correctly', async ({ page }) => {
    await scanPage.goto();

    // Test 1: package.json with enhanced resolution (should get transitive dependencies)
    await scanPage.uploadFile(path.join(__dirname, '../fixtures/package.json'));
    await scanPage.configureOptions({
      enhancedResolution: true
    });

    await scanPage.startScan();
    await scanPage.waitForScanToStart();
    await reportPage.waitForScanCompletion();

    const transitiveCount = await reportPage.getTotalDependenciesCount();

    // Go back and test without enhanced resolution
    await scanPage.goto();
    await scanPage.uploadFile(path.join(__dirname, '../fixtures/package.json'));
    await scanPage.configureOptions({
      enhancedResolution: false
    });

    await scanPage.startScan();
    await scanPage.waitForScanToStart();
    await reportPage.waitForScanCompletion();

    const directCount = await reportPage.getTotalDependenciesCount();

    // With transitive resolution, we should get more dependencies
    expect(transitiveCount).toBeGreaterThan(directCount);
  });
});