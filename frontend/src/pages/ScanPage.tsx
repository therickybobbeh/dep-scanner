import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, AlertCircle } from 'lucide-react';
import axios from 'axios';
import type { ScanRequest } from '../types/api';

const ScanPage: React.FC = () => {
  const [files, setFiles] = useState<Record<string, File>>({});
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState({
    include_dev_dependencies: true,
    ignore_severities: [] as string[],
  });
  
  const navigate = useNavigate();

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = event.target.files;
    if (!uploadedFiles) return;

    const newFiles: Record<string, File> = {};
    Array.from(uploadedFiles).forEach(file => {
      newFiles[file.name] = file;
    });
    
    setFiles(prev => ({ ...prev, ...newFiles }));
  }, []);

  const removeFile = useCallback((filename: string) => {
    setFiles(prev => {
      const updated = { ...prev };
      delete updated[filename];
      return updated;
    });
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    if (Object.keys(files).length === 0) {
      setError('Please upload at least one dependency file');
      return;
    }

    setIsUploading(true);

    try {
      // Read file contents
      const manifest_files: Record<string, string> = {};
      
      for (const [filename, file] of Object.entries(files)) {
        const content = await file.text();
        manifest_files[filename] = content;
      }

      const scanRequest: ScanRequest = {
        manifest_files,
        options: {
          include_dev_dependencies: options.include_dev_dependencies,
          ignore_severities: options.ignore_severities,
          ignore_rules: []
        }
      };

      const response = await axios.post('/api/scan', scanRequest);
      const { job_id } = response.data;

      // Redirect to scan results page
      navigate(`/report/${job_id}`);
    } catch (err) {
      console.error('Scan failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to start scan');
    } finally {
      setIsUploading(false);
    }
  };

  const supportedFiles = [
    'package.json', 'package-lock.json', 'yarn.lock',
    'requirements.txt', 'poetry.lock', 'Pipfile.lock', 'pyproject.toml'
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Start New Scan</h1>
        <p className="mt-2 text-gray-600">
          Upload your dependency files to scan for vulnerabilities
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* File Upload */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Upload Dependency Files</h2>
          
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
            <Upload className="mx-auto h-12 w-12 text-gray-400" />
            <div className="mt-4">
              <label htmlFor="file-upload" className="cursor-pointer">
                <span className="mt-2 block text-sm font-medium text-gray-900">
                  Drop files here or click to upload
                </span>
                <input
                  id="file-upload"
                  name="file-upload"
                  type="file"
                  multiple
                  className="sr-only"
                  accept=".json,.txt,.lock,.toml"
                  onChange={handleFileUpload}
                />
              </label>
            </div>
            <div className="mt-2">
              <p className="text-xs text-gray-500">
                Supported files: {supportedFiles.join(', ')}
              </p>
            </div>
          </div>

          {/* Uploaded Files */}
          {Object.keys(files).length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-medium text-gray-900 mb-2">Uploaded Files</h3>
              <div className="space-y-2">
                {Object.entries(files).map(([filename, file]) => (
                  <div
                    key={filename}
                    className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded"
                  >
                    <div className="flex items-center">
                      <FileText className="h-4 w-4 text-gray-400 mr-2" />
                      <span className="text-sm text-gray-900">{filename}</span>
                      <span className="text-xs text-gray-500 ml-2">
                        ({Math.round(file.size / 1024)}KB)
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeFile(filename)}
                      className="text-red-600 hover:text-red-800 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Scan Options */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Scan Options</h2>
          
          <div className="space-y-4">
            <div className="flex items-center">
              <input
                id="include-dev"
                name="include-dev"
                type="checkbox"
                checked={options.include_dev_dependencies}
                onChange={(e) => setOptions(prev => ({
                  ...prev,
                  include_dev_dependencies: e.target.checked
                }))}
                className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
              />
              <label htmlFor="include-dev" className="ml-2 block text-sm text-gray-900">
                Include development dependencies
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700">
                Ignore Severity Levels
              </label>
              <div className="mt-2 space-y-2">
                {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((severity) => (
                  <div key={severity} className="flex items-center">
                    <input
                      id={`ignore-${severity.toLowerCase()}`}
                      type="checkbox"
                      checked={options.ignore_severities.includes(severity)}
                      onChange={(e) => {
                        setOptions(prev => ({
                          ...prev,
                          ignore_severities: e.target.checked
                            ? [...prev.ignore_severities, severity]
                            : prev.ignore_severities.filter(s => s !== severity)
                        }));
                      }}
                      className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                    />
                    <label 
                      htmlFor={`ignore-${severity.toLowerCase()}`} 
                      className="ml-2 block text-sm text-gray-900"
                    >
                      {severity}
                    </label>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <AlertCircle className="h-5 w-5 text-red-400" />
              <div className="ml-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isUploading || Object.keys(files).length === 0}
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isUploading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Starting Scan...
              </>
            ) : (
              'Start Vulnerability Scan'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ScanPage;