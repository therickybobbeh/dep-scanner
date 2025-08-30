import React, { useState, useMemo } from 'react';
import { Table, Form, InputGroup, Button, Badge } from 'react-bootstrap';
import { ChevronDown, ChevronRight, Package, Search, ExternalLink } from 'lucide-react';
import SeverityBadge from './SeverityBadge';
import { SeverityLevel } from '../../types/common';
import './table.css';

interface Dependency {
  package: string;
  version: string;
  vulnerability_id?: string;
  severity?: string;
  severity_score?: number;
  cvss_score?: number; // Actual CVSS score for progress bars
  summary?: string;
  cve_ids?: string[];
  advisory_url?: string;
  fixed_range?: string;
  parent?: string;
  path?: string[];
  is_direct?: boolean;
  required_by?: string[];
  published?: string; // Published date for vulnerabilities
}

interface DependencyTableProps {
  dependencies: Dependency[];
  title?: string;
  showTransitive?: boolean;
  additionalFilters?: React.ReactNode;
}

const DependencyTable: React.FC<DependencyTableProps> = ({ 
  dependencies, 
  title = "Dependencies",
  additionalFilters 
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortColumn, setSortColumn] = useState<'package' | 'severity' | 'parent'>('severity');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [filterDirect, setFilterDirect] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState<SeverityLevel | 'all'>('all');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());

  const severityOrder: Record<string, number> = {
    'critical': 5,
    'high': 4,
    'medium': 3,
    'low': 2,
    'unknown': 1
  };

  const handleSort = (column: 'package' | 'severity' | 'parent') => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const toggleExpanded = (key: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedRows(newExpanded);
  };

  const filteredAndSorted = useMemo(() => {
    let filtered = [...dependencies];

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(dep => 
        dep.package.toLowerCase().includes(searchTerm.toLowerCase()) ||
        dep.version?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        dep.vulnerability_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        dep.cve_ids?.some(cve => cve.toLowerCase().includes(searchTerm.toLowerCase()))
      );
    }

    // Direct/transitive filter
    if (filterDirect) {
      filtered = filtered.filter(dep => dep.is_direct);
    }

    // Severity filter
    if (filterSeverity !== 'all') {
      filtered = filtered.filter(dep => dep.severity === filterSeverity);
    }

    // Sorting
    filtered.sort((a, b) => {
      let comparison = 0;
      
      switch (sortColumn) {
        case 'package':
          comparison = a.package.localeCompare(b.package);
          break;
        case 'severity':
          const aSeverity = severityOrder[a.severity?.toLowerCase() || 'unknown'] || 0;
          const bSeverity = severityOrder[b.severity?.toLowerCase() || 'unknown'] || 0;
          comparison = aSeverity - bSeverity;
          break;
        case 'parent':
          comparison = (a.parent || '').localeCompare(b.parent || '');
          break;
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });

    return filtered;
  }, [dependencies, searchTerm, sortColumn, sortDirection, filterDirect, filterSeverity]);

  const vulnerableCount = dependencies.filter(d => d.severity && d.severity !== 'unknown').length;
  const directCount = dependencies.filter(d => d.is_direct).length;
  const transitiveCount = dependencies.length - directCount;

  return (
    <div className="dependency-table-container">
      {/* Header with stats */}
      <div className="d-flex justify-content-between align-items-center mb-3">
        <h4 className="mb-0">{title}</h4>
        <div className="d-flex gap-2">
          <Badge bg="secondary">Total: {dependencies.length}</Badge>
          <Badge bg="primary">Direct: {directCount}</Badge>
          <Badge bg="info">Transitive: {transitiveCount}</Badge>
          {vulnerableCount > 0 && (
            <Badge bg="danger">Vulnerable: {vulnerableCount}</Badge>
          )}
        </div>
      </div>

      {/* Additional Filters */}
      {additionalFilters && (
        <div className="mb-3">
          {additionalFilters}
        </div>
      )}

      {/* Filters */}
      <div className="mb-3">
        <div className="row g-2">
          <div className="col-md-4">
            <InputGroup size="sm">
              <InputGroup.Text><Search size={16} /></InputGroup.Text>
              <Form.Control
                type="text"
                placeholder="Search packages, CVEs, IDs..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </InputGroup>
          </div>
          <div className="col-md-3">
            <Form.Select 
              size="sm" 
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value as SeverityLevel | 'all')}
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </Form.Select>
          </div>
          <div className="col-md-3">
            <Form.Check
              type="checkbox"
              label="Direct dependencies only"
              checked={filterDirect}
              onChange={(e) => setFilterDirect(e.target.checked)}
            />
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="table-responsive">
        <Table hover className="align-middle modern-data-table">
          <thead>
            <tr>
              <th style={{ width: '40px' }}></th>
              <th>
                <Button 
                  variant="link" 
                  className="p-0 text-decoration-none text-dark"
                  onClick={() => handleSort('package')}
                >
                  Package {sortColumn === 'package' && (sortDirection === 'asc' ? '↑' : '↓')}
                </Button>
              </th>
              <th>Version</th>
              <th>
                <Button 
                  variant="link" 
                  className="p-0 text-decoration-none text-dark"
                  onClick={() => handleSort('severity')}
                >
                  Severity {sortColumn === 'severity' && (sortDirection === 'asc' ? '↑' : '↓')}
                </Button>
              </th>
              <th>CVSS Score</th>
              <th>Type</th>
              <th>Vulnerability ID</th>
              <th>Published</th>
              <th>Quick Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSorted.map((dep, index) => {
              const key = `${dep.package}-${dep.version}-${index}`;
              const isExpanded = expandedRows.has(key);
              const hasDetails = dep.summary || dep.cve_ids?.length || dep.path?.length;

              return (
                <React.Fragment key={key}>
                  <tr 
                    className={hasDetails ? 'expandable-row' : ''}
                    tabIndex={hasDetails ? 0 : -1}
                    role={hasDetails ? 'button' : undefined}
                    aria-expanded={hasDetails ? isExpanded : undefined}
                    aria-controls={hasDetails ? `details-${key}` : undefined}
                    onKeyDown={(e) => {
                      if (hasDetails && (e.key === 'Enter' || e.key === ' ')) {
                        e.preventDefault();
                        toggleExpanded(key);
                      }
                    }}
                  >
                    <td>
                      {hasDetails && (
                        <Button
                          variant="link"
                          size="sm"
                          className="p-0 expand-icon"
                          onClick={() => toggleExpanded(key)}
                          aria-label={`${isExpanded ? 'Collapse' : 'Expand'} details for ${dep.package}`}
                        >
                          {isExpanded ? <ChevronDown size={16} className="expand-icon" /> : <ChevronRight size={16} className="expand-icon" />}
                        </Button>
                      )}
                    </td>
                    <td>
                      <div className="d-flex align-items-center gap-2">
                        <Package size={16} className="package-icon" />
                        <strong id={`package-${key}`}>{dep.package}</strong>
                      </div>
                    </td>
                    <td><code>{dep.version}</code></td>
                    <td>
                      {dep.severity ? (
                        <SeverityBadge severity={dep.severity as SeverityLevel} />
                      ) : (
                        <span className="text-muted">-</span>
                      )}
                    </td>
                    <td style={{ minWidth: '120px' }}>
                      {dep.cvss_score !== undefined && dep.cvss_score > 0 ? (
                        <div className="d-flex flex-column">
                          <div className="fw-bold mb-1">{dep.cvss_score.toFixed(1)}</div>
                          <div className="progress" style={{ height: '6px' }}>
                            <div 
                              className={`progress-bar ${
                                dep.cvss_score >= 9 ? 'bg-danger' :
                                dep.cvss_score >= 7 ? 'bg-warning' :
                                dep.cvss_score >= 4 ? 'bg-info' :
                                'bg-success'
                              }`}
                              role="progressbar"
                              style={{ width: `${(dep.cvss_score / 10) * 100}%` }}
                              aria-valuenow={dep.cvss_score}
                              aria-valuemin={0}
                              aria-valuemax={10}
                            ></div>
                          </div>
                        </div>
                      ) : (
                        <span className="text-muted">N/A</span>
                      )}
                    </td>
                    <td>
                      {dep.is_direct !== undefined ? (
                        dep.is_direct ? (
                          <Badge bg="primary">Direct</Badge>
                        ) : (
                          <Badge bg="secondary">Transitive</Badge>
                        )
                      ) : (
                        <Badge bg="light" text="dark">Unknown</Badge>
                      )}
                    </td>
                    <td>
                      {dep.vulnerability_id ? (
                        <code className="small text-muted">{dep.vulnerability_id}</code>
                      ) : (
                        <span className="text-muted">N/A</span>
                      )}
                    </td>
                    <td>
                      {dep.published ? (
                        new Date(dep.published).toLocaleDateString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric'
                        })
                      ) : (
                        <span className="text-muted">Unknown</span>
                      )}
                    </td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      <div className="d-flex gap-1">
                        {dep.advisory_url && (
                          <a
                            href={dep.advisory_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-sm btn-outline-primary"
                            title="View Advisory"
                          >
                            <ExternalLink size={14} />
                          </a>
                        )}
                        {dep.vulnerability_id && (
                          <a
                            href={`https://osv.dev/vulnerability/${dep.vulnerability_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="btn btn-sm btn-outline-success"
                            title="OSV Database"
                          >
                            OSV
                          </a>
                        )}
                      </div>
                    </td>
                  </tr>
                  {isExpanded && hasDetails && (
                    <tr className="expanded-content" id={`details-${key}`} role="region" aria-labelledby={`package-${key}`}>
                      <td colSpan={9} className="expanded-content">
                        <div className="p-3">
                          <div className="row">
                            <div className="col-md-8">
                              {dep.summary && (
                                <div className="mb-3">
                                  <strong className="text-primary">📄 Description:</strong>
                                  <div className="mt-1 text-muted">{dep.summary}</div>
                                </div>
                              )}
                              
                              {dep.fixed_range && (
                                <div className="mb-3">
                                  <strong className="text-success">🔧 Fix Available:</strong>
                                  <div className="mt-1">
                                    <Badge bg="success">
                                      Update to {dep.fixed_range}
                                    </Badge>
                                  </div>
                                </div>
                              )}
                              
                              {dep.cve_ids && dep.cve_ids.length > 0 && (
                                <div className="mb-3">
                                  <strong className="text-danger">🚨 CVE References:</strong>
                                  <div className="mt-1">
                                    {dep.cve_ids.map((cve, i) => (
                                      <a
                                        key={i}
                                        href={`https://nvd.nist.gov/vuln/detail/${cve}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="me-2 text-decoration-none"
                                      >
                                        <Badge bg="danger">{cve}</Badge>
                                      </a>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                            
                            <div className="col-md-4">
                              {!dep.is_direct && dep.parent && (
                                <div className="mb-3">
                                  <strong className="text-warning">📦 Parent Dependency:</strong>
                                  <div className="mt-1">
                                    <code className="bg-secondary text-dark p-1 rounded">
                                      {dep.parent}
                                    </code>
                                  </div>
                                </div>
                              )}
                              
                              {dep.path && dep.path.length > 1 && (
                                <div className="mb-3">
                                  <strong className="text-info">🔗 Dependency Path:</strong>
                                  <div className="mt-1">
                                    <code className="text-muted small d-block">
                                      {dep.path.join(' → ')}
                                    </code>
                                  </div>
                                </div>
                              )}
                              
                              <div className="d-flex flex-column gap-2">
                                {dep.advisory_url && (
                                  <a
                                    href={dep.advisory_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="btn btn-sm btn-outline-primary"
                                  >
                                    <ExternalLink size={14} className="me-1" />
                                    View Full Advisory
                                  </a>
                                )}
                                
                                {dep.vulnerability_id && (
                                  <a
                                    href={`https://osv.dev/vulnerability/${dep.vulnerability_id}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="btn btn-sm btn-outline-success"
                                  >
                                    View in OSV Database
                                  </a>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </Table>
      </div>

      {filteredAndSorted.length === 0 && (
        <div className="text-center py-5 text-muted">
          {searchTerm || filterSeverity !== 'all' || filterDirect ? (
            <>No dependencies match your filters</>
          ) : (
            <>No dependencies found</>
          )}
        </div>
      )}
    </div>
  );
};

export default DependencyTable;