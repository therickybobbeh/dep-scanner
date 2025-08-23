import React from 'react';
import { Link } from 'react-router-dom';
import { Shield, Zap, FileSearch, Download } from 'lucide-react';

const HomePage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Hero Section */}
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 sm:text-5xl md:text-6xl">
          Dependency Vulnerability Scanner
        </h1>
        <p className="mt-3 max-w-md mx-auto text-base text-gray-500 sm:text-lg md:mt-5 md:text-xl md:max-w-3xl">
          Scan your Python and JavaScript projects for known security vulnerabilities.
          Get detailed reports with fix recommendations.
        </p>
        <div className="mt-5 max-w-md mx-auto sm:flex sm:justify-center md:mt-8">
          <div className="rounded-md shadow">
            <Link
              to="/scan"
              className="w-full flex items-center justify-center px-8 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 md:py-4 md:text-lg md:px-10"
            >
              Start Scanning
            </Link>
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="py-12">
        <div className="max-w-xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-gray-900">Features</h2>
        </div>
        <div className="mt-10">
          <dl className="space-y-10 md:space-y-0 md:grid md:grid-cols-2 md:gap-x-8 md:gap-y-10">
            <div className="relative">
              <dt>
                <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                  <FileSearch className="h-6 w-6" />
                </div>
                <p className="ml-16 text-lg leading-6 font-medium text-gray-900">
                  Multi-Ecosystem Support
                </p>
              </dt>
              <dd className="mt-2 ml-16 text-base text-gray-500">
                Scans Python (pip, poetry, pipenv) and JavaScript (npm, yarn) projects
                with full transitive dependency resolution.
              </dd>
            </div>

            <div className="relative">
              <dt>
                <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                  <Shield className="h-6 w-6" />
                </div>
                <p className="ml-16 text-lg leading-6 font-medium text-gray-900">
                  OSV.dev Integration
                </p>
              </dt>
              <dd className="mt-2 ml-16 text-base text-gray-500">
                Uses Google's Open Source Vulnerabilities database for comprehensive
                and up-to-date vulnerability information.
              </dd>
            </div>

            <div className="relative">
              <dt>
                <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                  <Zap className="h-6 w-6" />
                </div>
                <p className="ml-16 text-lg leading-6 font-medium text-gray-900">
                  Fast & Efficient
                </p>
              </dt>
              <dd className="mt-2 ml-16 text-base text-gray-500">
                Batched API calls, intelligent caching, and deduplication ensure
                fast scan times even for large dependency trees.
              </dd>
            </div>

            <div className="relative">
              <dt>
                <div className="absolute flex items-center justify-center h-12 w-12 rounded-md bg-indigo-500 text-white">
                  <Download className="h-6 w-6" />
                </div>
                <p className="ml-16 text-lg leading-6 font-medium text-gray-900">
                  Multiple Export Formats
                </p>
              </dt>
              <dd className="mt-2 ml-16 text-base text-gray-500">
                Export scan results as JSON or CSV for integration with your
                existing security workflows and tools.
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Getting Started */}
      <div className="bg-gray-50 rounded-lg py-12 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Getting Started</h2>
          <p className="text-lg text-gray-600 mb-8">
            Ready to scan your project? Upload your dependency files or provide a repository path.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="font-semibold mb-2">1. Upload Files</h3>
              <p className="text-sm text-gray-600">
                Upload your package.json, requirements.txt, or lockfiles
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="font-semibold mb-2">2. Start Scan</h3>
              <p className="text-sm text-gray-600">
                Our scanner will analyze all dependencies for vulnerabilities
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <h3 className="font-semibold mb-2">3. Review Results</h3>
              <p className="text-sm text-gray-600">
                Get detailed reports with severity levels and fix recommendations
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;