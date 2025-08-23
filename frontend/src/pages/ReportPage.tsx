import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Download, Shield, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import axios from 'axios';
import type { ScanProgress, ScanReport } from '../types/api';

const ReportPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [progress, setProgress] = useState<ScanProgress | null>(null);
  const [report, setReport] = useState<ScanReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'severity' | 'package'>('severity');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  useEffect(() => {
    if (!jobId) return;

    const fetchStatus = async () => {
      try {
        const statusResponse = await axios.get(`/api/status/${jobId}`);
        const progressData: ScanProgress = statusResponse.data;
        setProgress(progressData);

        if (progressData.status === 'completed') {
          const reportResponse = await axios.get(`/api/report/${jobId}`);
          setReport(reportResponse.data);
          setLoading(false);
        } else if (progressData.status === 'failed') {
          setError(progressData.error_message || 'Scan failed');
          setLoading(false);
        } else {
          // Continue polling
          setTimeout(fetchStatus, 2000);
        }
      } catch (err) {
        console.error('Failed to fetch status:', err);
        setError('Failed to fetch scan status');
        setLoading(false);
      }
    };

    fetchStatus();
  }, [jobId]);

  const handleExport = async (format: 'json' | 'csv') => {
    if (!jobId) return;
    
    try {
      const response = await axios.get(`/api/export/${jobId}.${format}`, {
        responseType: 'blob',
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `depscan_report_${jobId}.${format}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const getSeverityColor = (severity: string | null) => {
    switch (severity) {
      case 'CRITICAL': return 'text-red-700 bg-red-100';
      case 'HIGH': return 'text-orange-700 bg-orange-100';
      case 'MEDIUM': return 'text-yellow-700 bg-yellow-100';
      case 'LOW': return 'text-blue-700 bg-blue-100';
      default: return 'text-gray-700 bg-gray-100';
    }
  };

  const getSeverityBadge = (severity: string | null) => {
    const colorClass = getSeverityColor(severity);
    return (
      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${colorClass}`}>
        {severity || 'UNKNOWN'}
      </span>
    );
  };

  const sortedVulnerabilities = React.useMemo(() => {
    if (!report) return [];
    
    let filtered = report.vulnerable_packages;
    
    if (filterSeverity !== 'all') {
      filtered = filtered.filter(v => v.severity === filterSeverity);
    }

    return filtered.sort((a, b) => {
      if (sortBy === 'severity') {
        const severityOrder = { 'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'UNKNOWN': 0 };
        const aSeverity = severityOrder[a.severity as keyof typeof severityOrder] || 0;
        const bSeverity = severityOrder[b.severity as keyof typeof severityOrder] || 0;
        return bSeverity - aSeverity;
      } else {
        return a.package.localeCompare(b.package);
      }
    });
  }, [report, sortBy, filterSeverity]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white shadow rounded-lg p-8">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            <h2 className="mt-4 text-lg font-medium text-gray-900">
              {progress?.current_step || 'Scanning dependencies...'}
            </h2>
            {progress && (
              <div className="mt-4">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress.progress_percent}%` }}
                  ></div>
                </div>
                <p className="mt-2 text-sm text-gray-500">
                  {Math.round(progress.progress_percent)}% complete
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Scan Failed</h3>
              <div className="mt-2 text-sm text-red-700">{error}</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <p className="text-yellow-800">No scan results available.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Scan Results</h1>
            <p className="mt-2 text-gray-600">
              Scan completed on {new Date(report.meta.generated_at).toLocaleDateString()}
            </p>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={() => handleExport('json')}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <Download className="h-4 w-4 mr-2" />
              Export JSON
            </button>
            <button
              onClick={() => handleExport('csv')}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Shield className="h-6 w-6 text-gray-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Total Dependencies</dt>
                  <dd className="text-lg font-medium text-gray-900">{report.total_dependencies}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <AlertTriangle className="h-6 w-6 text-red-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Vulnerable Packages</dt>
                  <dd className="text-lg font-medium text-gray-900">{report.vulnerable_count}</dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <CheckCircle className="h-6 w-6 text-green-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Clean Packages</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {report.total_dependencies - report.vulnerable_count}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Clock className="h-6 w-6 text-blue-400" />
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Ecosystems</dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {report.meta.ecosystems.join(', ')}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Vulnerabilities */}
      {report.vulnerable_count > 0 ? (
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          <div className="px-4 py-5 sm:px-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                Vulnerabilities Found
              </h3>
              <div className="flex space-x-4">
                <select
                  value={filterSeverity}
                  onChange={(e) => setFilterSeverity(e.target.value)}
                  className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                >
                  <option value="all">All Severities</option>
                  <option value="CRITICAL">Critical</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as 'severity' | 'package')}
                  className="block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                >
                  <option value="severity">Sort by Severity</option>
                  <option value="package">Sort by Package</option>
                </select>
              </div>
            </div>
          </div>
          <ul className="divide-y divide-gray-200">
            {sortedVulnerabilities.map((vuln, index) => (
              <li key={`${vuln.package}-${vuln.vulnerability_id}-${index}`} className="px-4 py-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center mb-2">
                      <h4 className="text-lg font-medium text-gray-900 mr-3">
                        {vuln.package}@{vuln.version}
                      </h4>
                      {getSeverityBadge(vuln.severity)}
                    </div>
                    
                    <div className="mb-3">
                      <p className="text-sm text-gray-600">{vuln.summary}</p>
                    </div>

                    <div className="flex flex-wrap gap-4 text-sm">
                      {vuln.vulnerability_id && (
                        <div>
                          <span className="font-medium text-gray-500">ID: </span>
                          <span className="text-gray-900">{vuln.vulnerability_id}</span>
                        </div>
                      )}
                      
                      {vuln.cve_ids.length > 0 && (
                        <div>
                          <span className="font-medium text-gray-500">CVE: </span>
                          <span className="text-gray-900">{vuln.cve_ids.join(', ')}</span>
                        </div>
                      )}
                      
                      {vuln.fixed_range && (
                        <div>
                          <span className="font-medium text-gray-500">Fix: </span>
                          <span className="text-green-600 font-medium">{vuln.fixed_range}</span>
                        </div>
                      )}
                    </div>

                    {vuln.advisory_url && (
                      <div className="mt-2">
                        <a
                          href={vuln.advisory_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-600 hover:text-indigo-500 text-sm"
                        >
                          View Advisory →
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="bg-green-50 border border-green-200 rounded-md p-8 text-center">
          <CheckCircle className="mx-auto h-12 w-12 text-green-400 mb-4" />
          <h3 className="text-lg font-medium text-green-800 mb-2">
            No Vulnerabilities Found!
          </h3>
          <p className="text-green-700">
            All {report.total_dependencies} dependencies are free of known security vulnerabilities.
          </p>
        </div>
      )}
    </div>
  );
};

export default ReportPage;