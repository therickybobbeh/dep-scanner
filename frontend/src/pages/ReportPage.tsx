import React, { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Download, Shield, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import axios from 'axios';
import { Container, Row, Col, Card, Button, ButtonGroup, Form, Alert, Badge } from 'react-bootstrap';
import ProgressBar from '../components/ui/ProgressBar';
import StatsCard from '../components/ui/StatsCard';
import SeverityBadge from '../components/ui/SeverityBadge';
import { SeverityLevel } from '../types/common';
import { groupBySeverity, sortBySeverity } from '../utils/severity';
import type { ScanProgress } from '../types/api';

// CLI JSON structure
interface CLIVulnerability {
  package: string;
  version: string;
  vulnerability_id: string;
  severity: string;
  summary: string;
  cve_ids: string[];
  advisory_url?: string;
  fixed_range?: string;
}

interface CLIReport {
  scan_info: {
    total_dependencies: number;
    vulnerable_packages: number;
    [key: string]: any;
  };
  vulnerabilities: CLIVulnerability[];
  [key: string]: any;
}

const ReportPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [progress, setProgress] = useState<ScanProgress | null>(null);
  const [report, setReport] = useState<CLIReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<'severity' | 'package'>('severity');
  const [filterSeverity, setFilterSeverity] = useState<SeverityLevel | 'all'>('all');

  useEffect(() => {
    if (!jobId) return;

    let pollCount = 0;
    const maxPollCount = 180; // 15 minutes max (180 * 5 seconds)

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
        } else if (pollCount < maxPollCount) {
          // Continue polling with 5 second intervals to avoid rate limiting
          pollCount++;
          setTimeout(fetchStatus, 5000);
        } else {
          setError('Scan timed out after 15 minutes');
          setLoading(false);
        }
      } catch (err: any) {
        console.error('Failed to fetch status:', err);
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

  const SeverityFilter: React.FC<{ counts: Record<SeverityLevel, number> }>=({ counts }) => (
    <ButtonGroup size="sm" role="group" aria-label="Filter vulnerabilities by severity">
      <Button 
        variant="light"
        className="text-primary"
        active={filterSeverity === 'all'}
        onClick={() => setFilterSeverity('all')}
      >
        All <Badge bg="light" text="dark" className="ms-2">{report?.vulnerabilities?.length ?? 0}</Badge>
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

  const sortedVulnerabilities = useMemo(() => {
    if (!report || !report.vulnerabilities) return [];
    
    let filtered = report.vulnerabilities;
    
    if (filterSeverity !== 'all') {
      filtered = filtered.filter(v => v.severity === filterSeverity);
    }

    if (sortBy === 'severity') {
      return sortBySeverity(filtered as any);
    }
    return [...filtered].sort((a, b) => a.package.localeCompare(b.package));
  }, [report, sortBy, filterSeverity]);

  if (loading) {
    return (
      <Container className="py-4">
        <Card className="scan-progress">
          <Card.Body className="text-center">
            <div className="mb-3">
              <div className="spinner-border text-primary" role="status" aria-hidden="true" />
            </div>
            <Card.Title className="mb-2">{progress?.current_step || 'Scanning dependencies...'}</Card.Title>
            {progress && (
              <div aria-live="polite" aria-label="Scan progress">
                <ProgressBar value={progress.progress_percent} />
                <div className="text-muted small mt-2">{Math.round(progress.progress_percent)}% complete</div>
              </div>
            )}
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
      {/* Header */}
      <Card className="border-0 shadow-sm mb-4">
        <Card.Body className="d-flex flex-wrap justify-content-between align-items-end">
          <div className="mb-3 mb-md-0">
            <h1 className="h2 fw-bold mb-1">Scan Results</h1>
            <div className="text-muted">Scan completed</div>
          </div>
          <div className="d-flex gap-2">
            <Button variant="light" size="sm" className="text-primary" onClick={handleExportJSON} aria-label="Export JSON">
              <Download size={16} className="me-2" /> Export Results
            </Button>
          </div>
        </Card.Body>
      </Card>

      {/* Summary Cards */}
      <Row className="g-3 mb-4">
        <Col md={3} xs={12}>
          <StatsCard title="Total Dependencies" value={report.scan_info.total_dependencies} icon={<Shield size={24} />} variant="primary" />
        </Col>
        <Col md={3} xs={12}>
          <StatsCard title="Vulnerable Packages" value={report.vulnerabilities.length} icon={<AlertTriangle size={24} />} variant="danger" />
        </Col>
        <Col md={3} xs={12}>
          <StatsCard title="Clean Packages" value={report.scan_info.total_dependencies - report.vulnerabilities.length} icon={<CheckCircle size={24} />} variant="success" />
        </Col>
        <Col md={3} xs={12}>
          <StatsCard title="Scan Type" value="CLI Scan" icon={<Clock size={24} />} variant="info" />
        </Col>
      </Row>

      {/* Vulnerabilities */}
      {report.vulnerabilities.length > 0 ? (
        <Card>
          <Card.Header className="d-flex flex-wrap justify-content-between align-items-center">
            <div className="h5 mb-0">Vulnerabilities Found</div>
            <div className="d-flex gap-2">
              {(() => {
                const counts = groupBySeverity(report.vulnerabilities as any);
                return <SeverityFilter counts={{
                  [SeverityLevel.CRITICAL]: counts[SeverityLevel.CRITICAL].length,
                  [SeverityLevel.HIGH]: counts[SeverityLevel.HIGH].length,
                  [SeverityLevel.MEDIUM]: counts[SeverityLevel.MEDIUM].length,
                  [SeverityLevel.LOW]: counts[SeverityLevel.LOW].length,
                  [SeverityLevel.UNKNOWN]: counts[SeverityLevel.UNKNOWN].length,
                }} />
              })()}
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
            {sortedVulnerabilities.map((vuln, index) => (
              <div key={`${vuln.package}-${vuln.vulnerability_id}-${index}`} className="p-3 border-bottom">
                <div className="d-flex flex-wrap justify-content-between align-items-start">
                  <div className="me-3">
                    <div className="d-flex align-items-center mb-2">
                      <div className="h5 mb-0 me-3">{vuln.package}@{vuln.version}</div>
                      <SeverityBadge severity={vuln.severity as SeverityLevel} />
                    </div>
                    <div className="text-muted small mb-2">{vuln.summary}</div>
                    <div className="d-flex flex-wrap gap-3 small">
                      {vuln.vulnerability_id && (
                        <div><span className="text-muted">ID:</span> <span className="fw-semibold">{vuln.vulnerability_id}</span></div>
                      )}
                      {vuln.cve_ids.length > 0 && (
                        <div><span className="text-muted">CVE:</span> <span className="fw-semibold">{vuln.cve_ids.join(', ')}</span></div>
                      )}
                      {vuln.fixed_range && (
                        <div><span className="text-muted">Fix:</span> <span className="text-success fw-medium">{vuln.fixed_range}</span></div>
                      )}
                    </div>
                    {vuln.advisory_url && (
                      <div className="mt-2">
                        <a href={vuln.advisory_url} target="_blank" rel="noopener noreferrer" className="link-primary small">
                          View Advisory →
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </Card.Body>
        </Card>
      ) : (
        <Card className="text-center">
          <Card.Body>
            <CheckCircle className="text-success mb-2" />
            <Card.Title>No Vulnerabilities Found</Card.Title>
            <Card.Text className="text-muted">
              All {report.scan_info.total_dependencies} dependencies are free of known security vulnerabilities.
            </Card.Text>
          </Card.Body>
        </Card>
      )}
    </Container>
  );
};

export default ReportPage;
