import React, { useState, useMemo } from 'react';
import { Table, Form, InputGroup, Button, Badge } from 'react-bootstrap';
import { ChevronDown, ChevronRight, Package, Search, ExternalLink } from 'lucide-react';
import SeverityBadge from './SeverityBadge';
import { SeverityLevel } from '../../types/common';

interface Dependency {
  package: string;
  version: string;
  vulnerability_id?: string;
  severity?: string;
  severity_score?: number;
  summary?: string;
  cve_ids?: string[];
  advisory_url?: string;
  fixed_range?: string;
  parent?: string;
  path?: string[];
  is_direct?: boolean;
  required_by?: string[];
}

interface DependencyTableProps {
  dependencies: Dependency[];
  title?: string;
  showTransitive?: boolean;
}

const DependencyTable: React.FC<DependencyTableProps> = ({ 
  dependencies, 
  title = "Dependencies",
  showTransitive = true 
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
        <Table hover striped className="align-middle">
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
              <th>Score</th>
              {showTransitive && (
                <th>
                  <Button 
                    variant="link" 
                    className="p-0 text-decoration-none text-dark"
                    onClick={() => handleSort('parent')}
                  >
                    Parent {sortColumn === 'parent' && (sortDirection === 'asc' ? '↑' : '↓')}
                  </Button>
                </th>
              )}
              <th>Type</th>
              <th>Details</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSorted.map((dep, index) => {
              const key = `${dep.package}-${dep.version}-${index}`;
              const isExpanded = expandedRows.has(key);
              const hasDetails = dep.summary || dep.cve_ids?.length || dep.path?.length;

              return (
                <React.Fragment key={key}>
                  <tr>
                    <td>
                      {hasDetails && (
                        <Button
                          variant="link"
                          size="sm"
                          className="p-0"
                          onClick={() => toggleExpanded(key)}
                        >
                          {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        </Button>
                      )}
                    </td>
                    <td>
                      <div className="d-flex align-items-center gap-2">
                        <Package size={16} className="text-muted" />
                        <strong>{dep.package}</strong>
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
                    <td>
                      {dep.severity_score !== undefined && dep.severity_score > 0 ? (
                        <Badge bg={dep.severity_score >= 7 ? 'danger' : dep.severity_score >= 4 ? 'warning' : 'success'}>
                          {dep.severity_score.toFixed(1)}
                        </Badge>
                      ) : (
                        <span className="text-muted">N/A</span>
                      )}
                    </td>
                    {showTransitive && (
                      <td>
                        {dep.parent ? (
                          <code className="small">{dep.parent}</code>
                        ) : dep.is_direct ? (
                          <Badge bg="primary" className="small">Root</Badge>
                        ) : (
                          <span className="text-muted">Unknown</span>
                        )}
                      </td>
                    )}
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
                      {dep.vulnerability_id && (
                        <small className="text-muted">{dep.vulnerability_id}</small>
                      )}
                      {dep.fixed_range && (
                        <div>
                          <Badge bg="success" className="small">Fix: {dep.fixed_range}</Badge>
                        </div>
                      )}
                    </td>
                    <td>
                      {dep.advisory_url && (
                        <Button
                          variant="link"
                          size="sm"
                          href={dep.advisory_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink size={14} />
                        </Button>
                      )}
                    </td>
                  </tr>
                  {isExpanded && hasDetails && (
                    <tr>
                      <td colSpan={showTransitive ? 9 : 8} className="bg-light">
                        <div className="p-3">
                          {dep.summary && (
                            <div className="mb-2">
                              <strong>Summary:</strong> {dep.summary}
                            </div>
                          )}
                          {dep.cve_ids && dep.cve_ids.length > 0 && (
                            <div className="mb-2">
                              <strong>CVE IDs:</strong>{' '}
                              {dep.cve_ids.map((cve, i) => (
                                <Badge key={i} bg="secondary" className="me-1">
                                  {cve}
                                </Badge>
                              ))}
                            </div>
                          )}
                                  {dep.path && dep.path.length > 1 && (
                            <div className="mb-2">
                              <strong>Dependency Path:</strong>
                              <div className="mt-1">
                                <code className="text-muted small">
                                  {dep.path.join(' → ')}
                                </code>
                              </div>
                            </div>
                          )}
                          {dep.required_by && dep.required_by.length > 0 && (
                            <div>
                              <strong>Required by:</strong>{' '}
                              {dep.required_by.map((pkg, i) => (
                                <Badge key={i} bg="info" className="me-1">
                                  {pkg}
                                </Badge>
                              ))}
                            </div>
                          )}
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