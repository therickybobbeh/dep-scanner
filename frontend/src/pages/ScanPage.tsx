import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Row, Col, Card, Form, Button, Alert, ListGroup, Badge, Spinner } from 'react-bootstrap';
import { Upload, FileText, X } from 'lucide-react';
import axios from 'axios';
import type { ScanRequest } from '../types/api';
import { SeverityLevel } from '../types/common';

const ScanPage: React.FC = () => {
  const [files, setFiles] = useState<Record<string, File>>({});
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState({
    include_dev_dependencies: true,
    ignore_severities: [] as SeverityLevel[],
    cache_control: {
      bypass_cache: false,
      use_enhanced_resolution: true, // Enable transitive dependencies by default
    }
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
          ignore_rules: [],
          cache_control: options.cache_control
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

            <Form.Group>
              <Form.Label className="fw-semibold">Cache Control Options</Form.Label>
              <div className="mt-2">
                <Form.Check
                  type="checkbox"
                  id="bypass-cache"
                  label="Bypass version resolution cache"
                  checked={options.cache_control.bypass_cache}
                  onChange={(e) => {
                    setOptions(prev => ({
                      ...prev,
                      cache_control: {
                        ...prev.cache_control,
                        bypass_cache: e.target.checked
                      }
                    }));
                  }}
                />
                <Form.Text className="text-muted d-block mb-2">
                  Force fresh version lookups from NPM registry (slower but most up-to-date)
                </Form.Text>
                
                <Form.Check
                  type="checkbox"
                  id="enhanced-resolution"
                  label="Enhanced version resolution with transitive dependencies"
                  checked={options.cache_control.use_enhanced_resolution}
                  onChange={(e) => {
                    setOptions(prev => ({
                      ...prev,
                      cache_control: {
                        ...prev.cache_control,
                        use_enhanced_resolution: e.target.checked
                      }
                    }));
                  }}
                />
                <Form.Text className="text-muted d-block">
                  Resolve package.json to include all transitive dependencies (recommended for comprehensive scans)
                </Form.Text>
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
