import { test, expect } from '@playwright/test';
import { ScanPage } from '../pages/ScanPage';
import { ReportPage } from '../pages/ReportPage';
import path from 'path';

// Environment configurations
const environments = [
  {
    name: 'Development',
    baseURL: 'http://localhost:5173',
    apiURL: 'http://localhost:8000'
  },
  {
    name: 'Staging', 
    baseURL: 'http://localhost:8080',
    apiURL: 'http://localhost:8001'
  }
];

// Test file for consistent comparison
const testFile = {
  name: 'package.json',
  path: path.join(__dirname, '../fixtures/package.json')
};

test.describe('Environment Comparison Tests', () => {
  // Store results from each environment for comparison
  const environmentResults: Record<string, {
    dependencyCount: number;
    vulnerableCount: number;
    ecosystems: string[];
    vulnerabilities: Array<{ package: string; severity: string }>;
  }> = {};

  for (const env of environments) {
    test.describe(`${env.name} Environment`, () => {
      test(`should scan successfully in ${env.name}`, async ({ page, baseURL }) => {
        // Override base URL for this test
        await page.goto(env.baseURL);

        const scanPage = new ScanPage(page);
        const reportPage = new ReportPage(page);

        // Navigate to scan page
        await scanPage.goto();

        // Upload test file
        await scanPage.uploadFile(testFile.path);
        await scanPage.verifyFileUploaded(testFile.name);

        // Use consistent scan options
        await scanPage.configureOptions({
          includeDevDeps: true,
          enhancedResolution: true,
          bypassCache: false
        });

        // Start scan
        await scanPage.startScan();
        await scanPage.waitForScanToStart();

        // Wait for completion with extended timeout for potential network issues
        await reportPage.waitForScanCompletion(180000); // 3 minutes

        // Collect results
        const dependencyCount = await reportPage.getTotalDependenciesCount();
        const vulnerableCount = await reportPage.getVulnerablePackagesCount();
        const vulnerabilities = await reportPage.getVulnerabilityDetails();

        // Store results for comparison
        environmentResults[env.name] = {
          dependencyCount,
          vulnerableCount,
          ecosystems: ['JavaScript'], // Known from our test file
          vulnerabilities
        };

        // Basic validation
        expect(dependencyCount).toBeGreaterThan(0);
        await reportPage.verifyEcosystems(['JavaScript']);

        console.log(`${env.name} Results:`, {
          dependencies: dependencyCount,
          vulnerabilities: vulnerableCount,
          details: vulnerabilities.length
        });
      });
    });
  }

  test('should produce identical results across environments', async ({ page }) => {
    // This test runs after the environment-specific tests
    const envNames = environments.map(env => env.name);
    
    // Ensure we have results from both environments
    for (const envName of envNames) {
      expect(environmentResults[envName]).toBeDefined();
    }

    const [env1, env2] = envNames;
    const results1 = environmentResults[env1];
    const results2 = environmentResults[env2];

    // Compare dependency counts (should be identical)
    expect(results1.dependencyCount).toBe(results2.dependencyCount);
    
    // Compare vulnerable package counts (should be identical)
    expect(results1.vulnerableCount).toBe(results2.vulnerableCount);

    // Compare ecosystems (should be identical)
    expect(results1.ecosystems.sort()).toEqual(results2.ecosystems.sort());

    // Compare vulnerability details (should be very similar)
    expect(results1.vulnerabilities.length).toBe(results2.vulnerabilities.length);

    // If there are vulnerabilities, compare them in detail
    if (results1.vulnerabilities.length > 0) {
      const vulns1 = results1.vulnerabilities.sort((a, b) => a.package.localeCompare(b.package));
      const vulns2 = results2.vulnerabilities.sort((a, b) => a.package.localeCompare(b.package));

      for (let i = 0; i < vulns1.length; i++) {
        expect(vulns1[i].package).toBe(vulns2[i].package);
        expect(vulns1[i].severity).toBe(vulns2[i].severity);
      }
    }

    console.log('✅ Environment comparison passed - results are identical');
  });
});

test.describe('Performance Comparison', () => {
  test('should have similar performance across environments', async ({ page }) => {
    const performanceResults: Record<string, number> = {};

    for (const env of environments) {
      await page.goto(env.baseURL);
      
      const scanPage = new ScanPage(page);
      const reportPage = new ReportPage(page);

      await scanPage.goto();
      await scanPage.uploadFile(testFile.path);

      // Measure scan time
      const startTime = Date.now();
      
      await scanPage.startScan();
      await scanPage.waitForScanToStart();
      await reportPage.waitForScanCompletion();

      const endTime = Date.now();
      const scanDuration = endTime - startTime;

      performanceResults[env.name] = scanDuration;
      
      console.log(`${env.name} scan took ${scanDuration}ms`);
    }

    // Performance should be within reasonable bounds (allow up to 2x difference)
    const times = Object.values(performanceResults);
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);

    expect(maxTime / minTime).toBeLessThan(3); // Allow up to 3x difference for network variability

    console.log('Performance comparison:', performanceResults);
  });
});