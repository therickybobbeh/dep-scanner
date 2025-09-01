import React, { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Download, Shield, AlertTriangle, CheckCircle, Clock, Table as TableIcon } from 'lucide-react';
import api from '../utils/api';
import { Container, Row, Col, Card, Button, ButtonGroup, Form, Alert, Badge, Nav } from 'react-bootstrap';
import StatsCard from '../components/ui/StatsCard';
import SeverityBadge from '../components/ui/SeverityBadge';
import DependencyTable from '../components/ui/DependencyTable';
import NewtonsCradleLoader from '../components/ui/NewtonsCradleLoader';
import { SeverityLevel } from '../types/common';
import { sortBySeverity } from '../utils/severity';
import type { ScanProgress } from '../types/api';
import '../styles/report.css';

// CLI JSON structure - updated to match actual CLI output
interface CLIVulnerability {
  package: string;
  version: string;
  vulnerability_id: string;
  severity: string;
  summary: string;
  cve_ids: string[];
  advisory_url?: string;
  fixed_range?: string;
  type?: string; // 'direct' or 'transitive'
  dependency_path?: string[];
  details?: string;
  published?: string;
  modified?: string;
  cvss_score?: number; // CVSS score 0.0-10.0
}

interface CLIReport {
  job_id: string;
  status: string;
  total_dependencies: number;
  vulnerable_count: number;
  vulnerable_packages: CLIVulnerability[];
  dependencies: any[];
  suppressed_count?: number;
  meta?: {
    generated_at: string;
    ecosystems: string[];
    scan_options: any;
  };
  scan_info?: {
    total_dependencies: number;
    vulnerable_packages: number;
    ecosystems: string[];
  };
  vulnerabilities?: CLIVulnerability[]; // Alternative structure from CLI
  [key: string]: any;
}

// Utility functions for CVSS and severity processing
const getCVSSScoreFromSeverity = (severity: string): number => {
  // Based on CLI implementation in backend/core/scanner/osv.py
  const scoreMap = {
    'CRITICAL': 9.5,
    'HIGH': 7.5,
    'MEDIUM': 5.0,
    'LOW': 2.5,
    'UNKNOWN': 0.0
  };
  return scoreMap[severity?.toUpperCase() as keyof typeof scoreMap] || 5.0;
};

const getCVSSRange = (severity: string): string => {
  // Based on CLI implementation in backend/core/reports.py
  const rangeMap = {
    'CRITICAL': '9.0 - 10.0',
    'HIGH': '7.0 - 8.9',
    'MEDIUM': '4.0 - 6.9',
    'LOW': '0.1 - 3.9',
    'UNKNOWN': 'No Score'
  };
  return rangeMap[severity?.toUpperCase() as keyof typeof rangeMap] || 'Unknown';
};

const formatPublishedDate = (dateString?: string): string => {
  if (!dateString) return 'Unknown';
  try {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  } catch {
    return 'Unknown';
  }
};

// Normalize CLI report data structure
const normalizeReportData = (report: CLIReport): CLIVulnerability[] => {
  // Handle both old and new CLI report formats
  let vulnerabilities: CLIVulnerability[] = [];
  
  if (report.vulnerable_packages && Array.isArray(report.vulnerable_packages)) {
    vulnerabilities = report.vulnerable_packages;
  } else if (report.vulnerabilities && Array.isArray(report.vulnerabilities)) {
    vulnerabilities = report.vulnerabilities;
  }
  
  // Ensure each vulnerability has required fields and CVSS scores
  return vulnerabilities.map(vuln => {
    // Use ONLY the CLI-provided type field - never guess or make up data
    let dependencyType = vuln.type;
    
    // If CLI didn't provide type field, this is a backend bug that needs fixing
    if (!dependencyType) {
      console.error(`Missing dependency type for package: ${vuln.package}`, vuln);
      dependencyType = 'unknown'; // Make it obvious something is wrong
    }
    
    return {
      ...vuln,
      cvss_score: vuln.cvss_score ?? getCVSSScoreFromSeverity(vuln.severity),
      type: dependencyType,
      cve_ids: vuln.cve_ids || [],
      dependency_path: vuln.dependency_path || [vuln.package]
    };
  });
};

const ReportPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [progress, setProgress] = useState<ScanProgress | null>(null);
  const [report, setReport] = useState<CLIReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'severity' | 'package'>('severity');
  const [filterSeverity, setFilterSeverity] = useState<SeverityLevel | 'all'>('all');
  const [viewMode, setViewMode] = useState<'cards' | 'table'>('table');

  useEffect(() => {
    if (!jobId) return;

    let pollCount = 0;
    const maxPollCount = 180; // 15 minutes max (180 * 5 seconds)

    const fetchStatus = async () => {
      try {
        const statusResponse = await api.get(`/status/${jobId}`);
        const progressData: ScanProgress = statusResponse.data;
        setProgress(progressData);

        if (progressData.status === 'completed') {
          const reportResponse = await api.get(`/report/${jobId}`);
          setReport(reportResponse.data);
          setLoading(false);
        } else if (progressData.status === 'failed') {
          setError(progressData.error_message || 'Scan failed');
          setLoading(false);
        } else if (pollCount < maxPollCount) {
          // Continue polling with 5 second intervals to avoid rate limiting
          pollCount++;
          setTimeout(fetchStatus, 5000);
        } else {
          setError('Scan timed out after 15 minutes');
          setLoading(false);
        }
      } catch (err: any) {
        if (err?.response?.status === 429) {
          // Rate limited - wait longer and retry
          if (pollCount < maxPollCount) {
            pollCount++;
            setTimeout(fetchStatus, 10000); // Wait 10 seconds on rate limit
          } else {
            setError('Scan timed out due to rate limiting');
            setLoading(false);
          }
        } else {
          setError('Failed to fetch scan status');
          setLoading(false);
        }
      }
    };

    fetchStatus();
  }, [jobId]);

  const handleExportJSON = async () => {
    if (!report) return;
    
    try {
      const dataStr = JSON.stringify(report, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = window.URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `depscan_report_${jobId}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const handleExportCSV = async () => {
    if (!report || !report.vulnerable_packages) return;
    
    try {
      // CSV headers
      const headers = [
        'Package',
        'Version', 
        'Vulnerability ID',
        'Severity',
        'Summary',
        'CVE IDs',
        'Advisory URL',
        'Fix Available',
        'Type',
        'Dependency Path'
      ];
      
      // Convert vulnerabilities to CSV rows
      const rows = report.vulnerable_packages.map(vuln => [
        vuln.package || '',
        vuln.version || '',
        vuln.vulnerability_id || '',
        vuln.severity || '',
        (vuln.summary || '').replace(/,/g, ';').replace(/\n/g, ' '), // Escape commas and newlines
        (vuln.cve_ids || []).join('; '),
        vuln.advisory_url || '',
        vuln.fixed_range || 'No fix available',
        vuln.type || 'unknown',
        (vuln.dependency_path || []).join(' → ')
      ]);
      
      // Combine headers and rows
      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(field => `"${field}"`).join(','))
      ].join('\n');
      
      // Create and download CSV file
      const dataBlob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
      const url = window.URL.createObjectURL(dataBlob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `depscan_report_${jobId}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('CSV export failed:', err);
    }
  };

  const SeverityFilter: React.FC<{ counts: Record<SeverityLevel, number> }>=({ counts }) => (
    <ButtonGroup size="sm" role="group" aria-label="Filter vulnerabilities by severity">
      <Button 
        variant="light"
        className="text-primary"
        active={filterSeverity === 'all'}
        onClick={() => setFilterSeverity('all')}
      >
        All <Badge bg="light" text="dark" className="ms-2">{report?.vulnerable_packages?.length ?? 0}</Badge>
      </Button>
      {Object.values(SeverityLevel).map(sev => (
        <Button
          key={sev}
          variant="light"
          className="text-primary text-uppercase"
          active={filterSeverity === sev}
          onClick={() => setFilterSeverity(sev as SeverityLevel)}
        >
          {sev} <Badge bg="light" text="dark" className="ms-2">{counts[sev as SeverityLevel] ?? 0}</Badge>
        </Button>
      ))}
    </ButtonGroup>
  );

  // Get normalized vulnerability data
  const normalizedVulnerabilities = useMemo(() => {
    if (!report) return [];
    return normalizeReportData(report);
  }, [report]);

  const sortedVulnerabilities = useMemo(() => {
    if (!normalizedVulnerabilities.length) return [];
    
    let filtered = normalizedVulnerabilities;
    
    if (filterSeverity !== 'all') {
      filtered = filtered.filter(v => {
        // Case-insensitive comparison for severity filtering
        const vulnSeverity = v.severity?.toUpperCase();
        const filterVal = filterSeverity.toUpperCase();
        return vulnSeverity === filterVal;
      });
    }

    if (sortBy === 'severity') {
      return sortBySeverity(filtered as any);
    }
    return [...filtered].sort((a, b) => a.package.localeCompare(b.package));
  }, [normalizedVulnerabilities, sortBy, filterSeverity]);

  // Enhanced statistics calculations matching CLI report
  const vulnerabilityStats = useMemo(() => {
    if (!normalizedVulnerabilities.length) {
      return {
        totalVulns: 0,
        uniquePackages: 0,
        totalDeps: report?.total_dependencies || report?.scan_info?.total_dependencies || 0,
        directDeps: 0,
        transitiveDeps: 0,
        avgCVSS: 0,
        maxCVSS: 0,
        severityCounts: { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, UNKNOWN: 0 }
      };
    }

    const uniquePackages = new Set(normalizedVulnerabilities.map(v => v.package));
    const cvssScores = normalizedVulnerabilities
      .map(v => v.cvss_score || getCVSSScoreFromSeverity(v.severity))
      .filter(score => score > 0);
    
    const severityCounts = { CRITICAL: 0, HIGH: 0, MEDIUM: 0, LOW: 0, UNKNOWN: 0 };
    normalizedVulnerabilities.forEach(v => {
      const sev = v.severity?.toUpperCase() as keyof typeof severityCounts;
      if (sev in severityCounts) {
        severityCounts[sev]++;
      } else {
        severityCounts.UNKNOWN++;
      }
    });

    const directCount = normalizedVulnerabilities.filter(v => v.type === 'direct').length;
    const totalDeps = report?.total_dependencies || report?.scan_info?.total_dependencies || 0;

    return {
      totalVulns: normalizedVulnerabilities.length,
      uniquePackages: uniquePackages.size,
      totalDeps,
      directDeps: directCount,
      transitiveDeps: normalizedVulnerabilities.length - directCount,
      avgCVSS: cvssScores.length ? cvssScores.reduce((a, b) => a + b, 0) / cvssScores.length : 0,
      maxCVSS: cvssScores.length ? Math.max(...cvssScores) : 0,
      severityCounts
    };
  }, [normalizedVulnerabilities, report]);

  if (loading) {
    return (
      <Container className="py-4">
        <Card className="border-0 shadow-sm">
          <Card.Body>
            <NewtonsCradleLoader 
              message={progress?.current_step || 'Processing...'}
            />
          </Card.Body>
        </Card>
      </Container>
    );
  }

  if (error) {
    return (
      <Container className="py-4">
        <Alert variant="danger">
          <AlertTriangle size={18} className="me-2" />
          <strong className="me-2">Scan Failed</strong>
          {error}
        </Alert>
      </Container>
    );
  }

  if (!report) {
    return (
      <Container className="py-4">
        <Alert variant="warning">No scan results available.</Alert>
      </Container>
    );
  }

  return (
    <Container className="py-4">
      {/* Enhanced Header matching CLI report */}
      <Card className="border-0 shadow-sm mb-4 report-header">
        <Card.Body className="report-header-content p-4">
          <div className="d-flex flex-wrap justify-content-between align-items-center">
            <div className="mb-3 mb-md-0">
              <h1 className="h1 fw-bold mb-2">🛡️ Dependency Security Report</h1>
              <div className="h5 fw-light opacity-75">Comprehensive vulnerability analysis</div>
              <div className="small opacity-75">
                Generated on {new Date().toLocaleDateString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric'
                })} at {new Date().toLocaleTimeString('en-US', {
                  hour: 'numeric',
                  minute: '2-digit',
                  hour12: true
                })}
              </div>
            </div>
            <div className="d-flex gap-2">
              <Button variant="light" size="sm" onClick={handleExportJSON} aria-label="Export JSON">
                <Download size={16} className="me-2" /> Export JSON
              </Button>
              <Button variant="light" size="sm" onClick={handleExportCSV} aria-label="Export CSV">
                <Download size={16} className="me-2" /> Export CSV
              </Button>
            </div>
          </div>
        </Card.Body>
      </Card>

      {/* Enhanced Summary Cards matching CLI report */}
      <Row className="g-3 mb-4">
        <Col lg={2} md={3} sm={6} xs={12}>
          <StatsCard title="Total Vulnerabilities" value={vulnerabilityStats.totalVulns} icon={<AlertTriangle size={24} />} variant="danger" />
        </Col>
        <Col lg={2} md={3} sm={6} xs={12}>
          <StatsCard title="Vulnerable Packages" value={vulnerabilityStats.uniquePackages} icon={<Shield size={24} />} variant="warning" />
        </Col>
        <Col lg={2} md={3} sm={6} xs={12}>
          <StatsCard title="Total Dependencies" value={vulnerabilityStats.totalDeps} icon={<CheckCircle size={24} />} variant="primary" />
        </Col>
        <Col lg={2} md={3} sm={6} xs={12}>
          <StatsCard title="Direct Dependencies" value={vulnerabilityStats.directDeps} icon={<Shield size={24} />} variant="info" />
        </Col>
        <Col lg={2} md={3} sm={6} xs={12}>
          <StatsCard title="Transitive Deps" value={vulnerabilityStats.transitiveDeps} icon={<Clock size={24} />} variant="secondary" />
        </Col>
        <Col lg={2} md={3} sm={6} xs={12}>
          <StatsCard 
            title="Average CVSS Score" 
            value={vulnerabilityStats.avgCVSS > 0 ? vulnerabilityStats.avgCVSS.toFixed(1) : '-'} 
            icon={<AlertTriangle size={24} />} 
            variant={vulnerabilityStats.avgCVSS >= 7 ? "danger" : vulnerabilityStats.avgCVSS >= 4 ? "warning" : "success"} 
          />
        </Col>
      </Row>

      {/* Severity Distribution Cards (matching CLI report) */}
      {vulnerabilityStats.totalVulns > 0 && (
        <Row className="g-3 mb-4">
          <Col xs={12}>
            <Card className="border-0 shadow-sm severity-breakdown-card">
              <Card.Header className="vulnerability-card-header">
                <h5 className="mb-0">📊 Executive Summary - Vulnerability Breakdown by Severity</h5>
              </Card.Header>
              <Card.Body className="summary-section">
                <Row className="g-3">
                  {Object.entries(vulnerabilityStats.severityCounts).map(([severity, count]) => {
                    if (count === 0) return null;
                    const percentage = ((count / vulnerabilityStats.totalVulns) * 100).toFixed(1);
                    const variant = severity === 'CRITICAL' ? 'danger' : 
                                  severity === 'HIGH' ? 'warning' : 
                                  severity === 'MEDIUM' ? 'info' : 
                                  severity === 'LOW' ? 'success' : 'secondary';
                    
                    return (
                      <Col lg={2} md={3} sm={4} xs={6} key={severity}>
                        <div className={`card border-${variant} h-100`}>
                          <div className="card-body text-center">
                            <div className={`display-6 fw-bold text-${variant} mb-1`}>{count}</div>
                            <div className="small text-muted mb-1">{percentage}%</div>
                            <div className={`fw-semibold text-${variant} text-uppercase small`}>{severity}</div>
                            <div className="text-muted small">{getCVSSRange(severity)}</div>
                          </div>
                        </div>
                      </Col>
                    );
                  })}
                </Row>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}

      {/* View Mode Toggle */}
      <Nav variant="tabs" className="mb-3">
        <Nav.Item>
          <Nav.Link 
            active={viewMode === 'table'} 
            onClick={() => setViewMode('table')}
          >
            <TableIcon size={16} className="me-2" />
            Table View
          </Nav.Link>
        </Nav.Item>
        <Nav.Item>
          <Nav.Link 
            active={viewMode === 'cards'} 
            onClick={() => setViewMode('cards')}
          >
            Cards View
          </Nav.Link>
        </Nav.Item>
      </Nav>

      {/* Vulnerabilities */}
      {viewMode === 'table' ? (
        // Table view using the new component
        <Card className="vulnerability-table">
          <Card.Body>
            <DependencyTable
              dependencies={normalizedVulnerabilities.map(vuln => {
                // Calculate parent from dependency path - fixed logic
                const parent = vuln.dependency_path && vuln.dependency_path.length > 1 
                  ? vuln.dependency_path[vuln.dependency_path.length - 2]
                  : undefined;
                
                // Use actual CVSS score or calculated from severity
                const cvssScore = vuln.cvss_score || getCVSSScoreFromSeverity(vuln.severity);
                
                return {
                  package: vuln.package,
                  version: vuln.version,
                  vulnerability_id: vuln.vulnerability_id,
                  severity: vuln.severity,
                  severity_score: cvssScore, // Use actual CVSS score
                  summary: vuln.summary,
                  cve_ids: vuln.cve_ids || [],
                  advisory_url: vuln.advisory_url,
                  fixed_range: vuln.fixed_range,
                  is_direct: vuln.type === 'direct', // Fixed dependency type classification
                  parent: parent,
                  path: vuln.dependency_path || [vuln.package],
                  required_by: [], // Could be calculated from dependency tree if needed
                  published: vuln.published, // Add published date
                  cvss_score: cvssScore // Explicit CVSS score for progress bars
                };
              })}
              title={`Vulnerability Report (${vulnerabilityStats.totalVulns} vulnerabilities across ${vulnerabilityStats.uniquePackages} packages)`}
              showTransitive={true}
              additionalFilters={
                <div className="d-flex flex-wrap gap-2 mb-3">
                  <div className="fw-bold me-2">Filter by Severity:</div>
                  <ButtonGroup size="sm">
                    <Button 
                      variant={filterSeverity === 'all' ? 'primary' : 'outline-secondary'}
                      onClick={() => setFilterSeverity('all')}
                    >
                      All ({vulnerabilityStats.totalVulns})
                    </Button>
                    {Object.entries(vulnerabilityStats.severityCounts).map(([sev, count]) => {
                      if (count === 0) return null;
                      const variant = sev === 'CRITICAL' ? 'danger' : 
                                    sev === 'HIGH' ? 'warning' : 
                                    sev === 'MEDIUM' ? 'info' : 
                                    sev === 'LOW' ? 'success' : 'secondary';
                      const isActive = filterSeverity === sev.toLowerCase();
                      
                      return (
                        <Button
                          key={sev}
                          variant={isActive ? variant : `outline-${variant}`}
                          onClick={() => setFilterSeverity(sev.toLowerCase() as SeverityLevel)}
                        >
                          {sev} ({count})
                        </Button>
                      );
                    })}
                  </ButtonGroup>
                </div>
              }
            />
          </Card.Body>
        </Card>
      ) : normalizedVulnerabilities.length > 0 ? (
        <Card className="vulnerability-card">
          <Card.Header className="vulnerability-card-header d-flex flex-wrap justify-content-between align-items-center">
            <div className="h5 mb-0">🚨 Detailed Vulnerabilities ({vulnerabilityStats.totalVulns} findings across {vulnerabilityStats.uniquePackages} packages)</div>
            <div className="d-flex gap-2">
              <SeverityFilter counts={{
                [SeverityLevel.CRITICAL]: vulnerabilityStats.severityCounts.CRITICAL,
                [SeverityLevel.HIGH]: vulnerabilityStats.severityCounts.HIGH,
                [SeverityLevel.MEDIUM]: vulnerabilityStats.severityCounts.MEDIUM,
                [SeverityLevel.LOW]: vulnerabilityStats.severityCounts.LOW,
                [SeverityLevel.UNKNOWN]: vulnerabilityStats.severityCounts.UNKNOWN,
              }} />
              <Form.Select
                size="sm"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'severity' | 'package')}
                aria-label="Sort vulnerabilities"
              >
                <option value="severity">Sort by Severity</option>
                <option value="package">Sort by Package</option>
              </Form.Select>
            </div>
          </Card.Header>
          <Card.Body className="p-0">
            {sortedVulnerabilities.map((vuln, index) => {
              const cvssScore = vuln.cvss_score || getCVSSScoreFromSeverity(vuln.severity);
              const publishedDate = formatPublishedDate(vuln.published);
              
              return (
                <div key={`${vuln.package}-${vuln.vulnerability_id}-${index}`} className="p-3 border-bottom">
                  <div className="d-flex flex-wrap justify-content-between align-items-start">
                    <div className="me-3 flex-grow-1">
                      <div className="d-flex align-items-center mb-2 flex-wrap gap-2">
                        <div className="h5 mb-0 me-2">{vuln.package}@{vuln.version}</div>
                        <SeverityBadge severity={vuln.severity as SeverityLevel} />
                        {cvssScore > 0 && (
                          <Badge bg={cvssScore >= 7 ? 'danger' : cvssScore >= 4 ? 'warning' : 'success'}>
                            CVSS {cvssScore.toFixed(1)}
                          </Badge>
                        )}
                        <Badge bg={vuln.type === 'direct' ? 'primary' : 'secondary'}>
                          {vuln.type === 'direct' ? 'Direct' : 'Transitive'}
                        </Badge>
                      </div>
                      <div className="text-muted mb-2">{vuln.summary}</div>
                      <div className="d-flex flex-wrap gap-3 small mb-2">
                        {vuln.vulnerability_id && (
                          <div><span className="text-muted">ID:</span> <span className="fw-semibold">{vuln.vulnerability_id}</span></div>
                        )}
                        {vuln.cve_ids && vuln.cve_ids.length > 0 && (
                          <div><span className="text-muted">CVE:</span> <span className="fw-semibold">{vuln.cve_ids.join(', ')}</span></div>
                        )}
                        {vuln.published && (
                          <div><span className="text-muted">Published:</span> <span className="fw-semibold">{publishedDate}</span></div>
                        )}
                        {vuln.fixed_range && (
                          <div><span className="text-muted">Fix:</span> <span className="text-success fw-medium">{vuln.fixed_range}</span></div>
                        )}
                      </div>
                      <div className="d-flex flex-wrap gap-2">
                        {vuln.advisory_url && (
                          <a href={vuln.advisory_url} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-outline-primary">
                            View Advisory
                          </a>
                        )}
                        {vuln.vulnerability_id && (
                          <a href={`https://osv.dev/vulnerability/${vuln.vulnerability_id}`} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-outline-success">
                            OSV Database
                          </a>
                        )}
                        {vuln.cve_ids && vuln.cve_ids.length > 0 && (
                          <a href={`https://nvd.nist.gov/vuln/detail/${vuln.cve_ids[0]}`} target="_blank" rel="noopener noreferrer" className="btn btn-sm btn-outline-danger">
                            {vuln.cve_ids[0]}
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </Card.Body>
        </Card>
      ) : (
        <Card className="text-center">
          <Card.Body>
            <CheckCircle className="text-success mb-2" />
            <Card.Title>No Vulnerabilities Found</Card.Title>
            <Card.Text className="text-muted">
              All {report?.total_dependencies || 0} dependencies are free of known security vulnerabilities.
            </Card.Text>
          </Card.Body>
        </Card>
      )}
    </Container>
  );
};

export default ReportPage;
