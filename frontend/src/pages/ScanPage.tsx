import React, { useState, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Row, Col, Card, Form, Button, Alert, ListGroup, Badge, Spinner } from 'react-bootstrap';
import { Upload, FileText, X, CheckCircle, AlertTriangle } from 'lucide-react';
import axios from 'axios';
import type { ScanRequest } from '../types/api';
import { SeverityLevel } from '../types/common';

const ScanPage: React.FC = () => {
  const [files, setFiles] = useState<Record<string, File>>({});
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [consistencyResult, setConsistencyResult] = useState<any>(null);
  const [isValidatingConsistency, setIsValidatingConsistency] = useState(false);
  const [options, setOptions] = useState({
    include_dev_dependencies: true,
    ignore_severities: [] as SeverityLevel[],
  });
  
  const navigate = useNavigate();

  // Check if both package.json and package-lock.json are uploaded
  const hasBothPackageFiles = useMemo(() => {
    const fileNames = Object.keys(files);
    return fileNames.includes('package.json') && fileNames.includes('package-lock.json');
  }, [files]);

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

  const validateConsistency = async () => {
    if (!hasBothPackageFiles) return;
    
    setConsistencyResult(null);
    setIsValidatingConsistency(true);
    setError(null);
    
    try {
      // Read file contents
      const manifest_files: Record<string, string> = {};
      
      for (const [filename, file] of Object.entries(files)) {
        if (filename === 'package.json' || filename === 'package-lock.json') {
          const content = await file.text();
          manifest_files[filename] = content;
        }
      }

      const consistencyRequest = {
        manifest_files,
        options: {
          include_dev_dependencies: options.include_dev_dependencies,
          ignore_severities: options.ignore_severities,
          ignore_rules: []
        }
      };

      const response = await axios.post('/api/validate-consistency', consistencyRequest);
      setConsistencyResult(response.data);
    } catch (err) {
      console.error('Consistency validation failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to validate consistency');
    } finally {
      setIsValidatingConsistency(false);
    }
  };


  const supportedFiles = [
    'package.json', 'package-lock.json', 'yarn.lock',
    'requirements.txt', 'poetry.lock', 'Pipfile.lock', 'pyproject.toml'
  ];

  return (
    <Container className="py-4" style={{ maxWidth: '800px' }}>
      <Row className="mb-4">
        <Col>
          <Card className="border-0 shadow-sm">
            <Card.Body>
              <h1 className="display-6 fw-bold mb-2">Start New Scan</h1>
              <p className="lead mb-0">
                Upload your dependency files to scan for vulnerabilities
              </p>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Form onSubmit={handleSubmit}>
        {/* File Upload */}
        <Card className="mb-4">
          <Card.Header>
            <Card.Title className="mb-0">Upload Dependency Files</Card.Title>
          </Card.Header>
          <Card.Body>
            <div className="border border-2 border-dashed rounded p-4 text-center" style={{ borderColor: 'var(--bs-border-color)', backgroundColor: 'var(--bs-tertiary-bg)' }}>
              <Upload size={48} className="mx-auto mb-3 text-muted" />
              <Form.Group>
                <Form.Label htmlFor="file-upload" className="btn btn-outline-primary mb-2">
                  Drop files here or click to upload
                </Form.Label>
                <Form.Control
                  id="file-upload"
                  name="file-upload"
                  type="file"
                  multiple
                  hidden
                  accept=".json,.txt,.lock,.toml"
                  onChange={handleFileUpload}
                />
              </Form.Group>
              <small className="text-muted d-block">
                Supported files: {supportedFiles.join(', ')}
              </small>
            </div>

            {/* Uploaded Files */}
            {Object.keys(files).length > 0 && (
              <div className="mt-4">
                <h6 className="fw-semibold mb-2">Uploaded Files</h6>
                <ListGroup>
                  {Object.entries(files).map(([filename, file]) => (
                    <ListGroup.Item
                      key={filename}
                      className="d-flex justify-content-between align-items-center"
                    >
                      <div className="d-flex align-items-center">
                        <FileText size={16} className="me-2 text-muted" />
                        <span className="fw-medium">{filename}</span>
                        <Badge bg="light" text="muted" className="ms-2">
                          {Math.round(file.size / 1024)}KB
                        </Badge>
                      </div>
                      <Button
                        variant="outline-danger"
                        size="sm"
                        onClick={() => removeFile(filename)}
                      >
                        <X size={14} />
                      </Button>
                    </ListGroup.Item>
                  ))}
                </ListGroup>
              </div>
            )}
          </Card.Body>
        </Card>

        {/* Consistency Validation */}
        {hasBothPackageFiles && (
          <Card className="mb-4">
            <Card.Header className="bg-info-subtle">
              <Card.Title className="mb-0 d-flex align-items-center">
                <CheckCircle size={18} className="me-2 text-info" />
                Package Consistency Validation
              </Card.Title>
            </Card.Header>
            <Card.Body>
              <div className="d-flex align-items-start">
                <div className="flex-grow-1">
                  <p className="mb-2">
                    Both <code>package.json</code> and <code>package-lock.json</code> detected. 
                    Validate that they produce consistent vulnerability scan results.
                  </p>
                  <small className="text-muted">
                    This checks for differences in version resolution that might cause inconsistent results.
                  </small>
                </div>
                <Button
                  variant="info"
                  size="sm"
                  onClick={validateConsistency}
                  disabled={isValidatingConsistency}
                  className="ms-3"
                >
                  {isValidatingConsistency ? (
                    <>
                      <Spinner as="span" animation="border" size="sm" className="me-2" />
                      Validating...
                    </>
                  ) : (
                    <>
                      <CheckCircle size={16} className="me-2" />
                      Validate Consistency
                    </>
                  )}
                </Button>
              </div>
              
              {/* Consistency Results */}
              {consistencyResult && (
                <div className="mt-3">
                  <Alert 
                    variant={consistencyResult.is_consistent ? 'success' : 'warning'}
                    className="mb-3"
                  >
                    <div className="d-flex align-items-center">
                      {consistencyResult.is_consistent ? (
                        <CheckCircle size={18} className="me-2" />
                      ) : (
                        <AlertTriangle size={18} className="me-2" />
                      )}
                      <strong>
                        {consistencyResult.is_consistent 
                          ? 'Files are consistent' 
                          : 'Inconsistencies detected'}
                      </strong>
                    </div>
                  </Alert>
                  
                  {/* Metrics Comparison */}
                  {consistencyResult.analysis?.metrics && (
                    <div className="row mb-3">
                      <div className="col-md-6">
                        <Card className="border-primary">
                          <Card.Header className="bg-primary-subtle">
                            <small className="fw-semibold">package.json</small>
                          </Card.Header>
                          <Card.Body className="py-2">
                            <div className="d-flex justify-content-between">
                              <span>Vulnerabilities:</span>
                              <Badge bg="danger">{consistencyResult.analysis.metrics.package_json.vulnerabilities}</Badge>
                            </div>
                            <div className="d-flex justify-content-between">
                              <span>Dependencies:</span>
                              <Badge bg="info">{consistencyResult.analysis.metrics.package_json.dependencies}</Badge>
                            </div>
                          </Card.Body>
                        </Card>
                      </div>
                      <div className="col-md-6">
                        <Card className="border-success">
                          <Card.Header className="bg-success-subtle">
                            <small className="fw-semibold">package-lock.json</small>
                          </Card.Header>
                          <Card.Body className="py-2">
                            <div className="d-flex justify-content-between">
                              <span>Vulnerabilities:</span>
                              <Badge bg="danger">{consistencyResult.analysis.metrics.package_lock.vulnerabilities}</Badge>
                            </div>
                            <div className="d-flex justify-content-between">
                              <span>Dependencies:</span>
                              <Badge bg="info">{consistencyResult.analysis.metrics.package_lock.dependencies}</Badge>
                            </div>
                          </Card.Body>
                        </Card>
                      </div>
                    </div>
                  )}
                  
                  {/* Recommendations */}
                  {consistencyResult.recommendations && consistencyResult.recommendations.length > 0 && (
                    <div className="mb-2">
                      <h6 className="fw-semibold mb-2">Recommendations:</h6>
                      <ul className="mb-0 small">
                        {consistencyResult.recommendations.slice(0, 3).map((rec: string, index: number) => (
                          <li key={index}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  {/* Warnings */}
                  {consistencyResult.warnings && consistencyResult.warnings.length > 0 && (
                    <div>
                      <h6 className="fw-semibold mb-2 text-warning">Warnings:</h6>
                      <ul className="mb-0 small text-muted">
                        {consistencyResult.warnings.slice(0, 3).map((warning: string, index: number) => (
                          <li key={index}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </Card.Body>
          </Card>
        )}

        {/* Scan Options */}
        <Card className="mb-4">
          <Card.Header>
            <Card.Title className="mb-0">Scan Options</Card.Title>
          </Card.Header>
          <Card.Body>
            <Form.Group className="mb-3">
              <Form.Check
                type="checkbox"
                id="include-dev"
                label="Include development dependencies"
                checked={options.include_dev_dependencies}
                onChange={(e) => setOptions(prev => ({
                  ...prev,
                  include_dev_dependencies: e.target.checked
                }))}
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label className="fw-semibold">Ignore Severity Levels</Form.Label>
              <div className="mt-2">
                {[SeverityLevel.LOW, SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL].map((severity) => (
                  <Form.Check
                    key={severity}
                    type="checkbox"
                    id={`ignore-${severity.toLowerCase()}`}
                    label={severity}
                    checked={options.ignore_severities.includes(severity)}
                    onChange={(e) => {
                      setOptions(prev => ({
                        ...prev,
                        ignore_severities: e.target.checked
                          ? [...prev.ignore_severities, severity]
                          : prev.ignore_severities.filter(s => s !== severity)
                      }));
                    }}
                  />
                ))}
              </div>
            </Form.Group>

          </Card.Body>
        </Card>

        {/* Error Display */}
        {error && (
          <Alert variant="danger" className="mb-4">
            <Alert.Heading>Error</Alert.Heading>
            <p className="mb-0">{error}</p>
          </Alert>
        )}

        {/* Submit Button */}
        <div className="d-flex justify-content-end">
          <Button
            type="submit"
            variant="light"
            className="text-primary"
            size="lg"
            disabled={isUploading || Object.keys(files).length === 0}
          >
            {isUploading ? (
              <>
                <Spinner as="span" animation="border" size="sm" className="me-2" />
                Starting Scan...
              </>
            ) : (
              'Start Vulnerability Scan'
            )}
          </Button>
        </div>
      </Form>
    </Container>
  );
};

export default ScanPage;