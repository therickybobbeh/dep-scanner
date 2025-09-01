import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Row, Col, Card, Form, Button, Alert, ListGroup, Badge } from 'react-bootstrap';
import { Upload, FileText, X } from 'lucide-react';
import { ScanLoadingModal } from '../components/ui';
import type { ScanRequest } from '../types/api';
import { SeverityLevel } from '../types/common';

const ScanPage: React.FC = () => {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showLoadingModal, setShowLoadingModal] = useState(false);
  const [scanRequest, setScanRequest] = useState<ScanRequest | null>(null);
  const [options, setOptions] = useState({
    include_dev_dependencies: true,
    ignore_severities: [] as SeverityLevel[],
  });
  const [isScanning, setIsScanning] = useState(false);
  

  const handleFileUpload = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = event.target.files;
    if (!uploadedFiles || uploadedFiles.length === 0) return;

    // Take only the first file since we only allow single file upload
    const selectedFile = uploadedFiles[0];
    setFile(selectedFile);
    setError(null); // Clear any previous errors
  }, []);

  const removeFile = useCallback(() => {
    setFile(null);
    setError(null);
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    try {
      // Validate file upload
      if (!file) {
        setError('Please upload a manifest file (package.json, requirements.txt, etc.)');
        return;
      }

      // Validate file size
      if (file.size === 0) {
        setError(`File ${file.name} is empty`);
        return;
      }

      // Read and validate file content
      const content = await file.text();
      
      if (!content.trim()) {
        setError(`File ${file.name} is empty`);
        return;
      }

      // Check for obviously invalid content
      if (content.trim() === '{}') {
        setError(`File ${file.name} contains only empty JSON object`);
        return;
      }

      // Validate JSON files
      if (file.name.endsWith('.json')) {
        try {
          const parsed = JSON.parse(content);
          
          // For package.json, verify it has expected structure
          if (file.name === 'package.json') {
            if (!parsed.name && !parsed.dependencies && !parsed.devDependencies) {
              console.warn('package.json appears to be missing standard fields');
            }
          }
        } catch (jsonError) {
          setError(`File ${file.name} contains invalid JSON: ${jsonError instanceof Error ? jsonError.message : 'Unknown JSON error'}`);
          return;
        }
      }

      // Create scan request
      const newScanRequest: ScanRequest = {
        manifest_files: {
          [file.name]: content
        },
        options: {
          include_dev_dependencies: options.include_dev_dependencies,
          ignore_severities: options.ignore_severities,
          ignore_rules: []
        }
      };

      // Store scan request and show loading modal
      setScanRequest(newScanRequest);
      setShowLoadingModal(true);
      setIsScanning(true);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to prepare scan');
      setIsScanning(false); // Reset scanning state on error
    }
  };


  // Modal handlers
  const handleModalSuccess = (jobId: string) => {
    setShowLoadingModal(false);
    setScanRequest(null);
    setIsScanning(false);
    navigate(`/report/${jobId}`);
  };

  const handleModalClose = () => {
    setShowLoadingModal(false);
    setScanRequest(null);
    setIsScanning(false);
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
              <p className="lead">
                Upload a dependency file to scan for vulnerabilities
              </p>
              <p className="text-muted mb-0">
                <small>
                  ⏱️ Note: Security scans query the OSV database and may take a few minutes depending on the number of dependencies
                </small>
              </p>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Form onSubmit={handleSubmit}>
        {/* File Upload */}
        <Card className="mb-4">
          <Card.Header>
            <Card.Title className="mb-0">Upload Dependency File</Card.Title>
          </Card.Header>
          <Card.Body>
            <div className="border border-2 border-dashed rounded p-4 text-center" style={{ borderColor: 'var(--bs-border-color)', backgroundColor: 'var(--bs-tertiary-bg)' }}>
              <Upload size={48} className="mx-auto mb-3 text-muted" />
              <Form.Group>
                <Form.Label htmlFor="file-upload" className="btn btn-outline-primary mb-2">
                  Drop file here or click to upload
                </Form.Label>
                <Form.Control
                  id="file-upload"
                  name="file-upload"
                  type="file"
                  hidden
                  accept=".json,.txt,.lock,.toml"
                  onChange={handleFileUpload}
                />
              </Form.Group>
              <small className="text-muted d-block">
                Supported files: {supportedFiles.join(', ')}
              </small>
            </div>

            {/* Uploaded File */}
            {file && (
              <div className="mt-4">
                <h6 className="fw-semibold mb-2">Uploaded File</h6>
                <ListGroup>
                  <ListGroup.Item className="d-flex justify-content-between align-items-center">
                    <div className="d-flex align-items-center">
                      <FileText size={16} className="me-2 text-muted" />
                      <span className="fw-medium">{file.name}</span>
                      <Badge bg="light" text="muted" className="ms-2">
                        {Math.round(file.size / 1024)}KB
                      </Badge>
                    </div>
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={removeFile}
                    >
                      <X size={14} />
                    </Button>
                  </ListGroup.Item>
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
        <div className="d-flex flex-column align-items-end">
          <small className="text-muted mb-2">
            🔍 Scanning may take 2-5 minutes depending on project size
          </small>
          <Button
            type="submit"
            variant="light"
            className="text-primary"
            size="lg"
            disabled={!file}
          >
            Start Vulnerability Scan
          </Button>
        </div>
      </Form>
      
      {/* Loading Modal */}
      {showLoadingModal && scanRequest && (
        <ScanLoadingModal
          show={showLoadingModal}
          onHide={handleModalClose}
          onSuccess={handleModalSuccess}
          scanRequest={scanRequest}
        />
      )}
    </Container>
  );
};

export default ScanPage;