import React from 'react';
import { Link } from 'react-router-dom';
import { Container, Row, Col, Button, Card } from 'react-bootstrap';
import { Shield, Zap, FileSearch, Download } from 'lucide-react';

const HomePage: React.FC = () => {
  return (
    <Container className="py-5">
      {/* Hero Section */}
      <Row className="mb-5">
        <Col md={{ span: 10, offset: 1 }} lg={{ span: 8, offset: 2 }}>
          <Card className="border-0 shadow-sm text-center">
            <Card.Body className="p-5">
              <h1 className="display-3 fw-bold mb-3">
                Dependency Vulnerability Scanner
              </h1>
              <p className="lead text-muted mb-4 mx-auto" style={{ maxWidth: '600px' }}>
                Scan your Python and JavaScript projects for known security vulnerabilities.
                Get detailed reports with fix recommendations.
              </p>
              <Button 
                as={Link as any} 
                to="/scan" 
                variant="primary" 
                size="lg" 
                className="px-5 py-3"
              >
                Start Scanning
              </Button>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Features */}
      <Row className="mb-5">
        <Col className="text-center mb-4">
          <h2 className="display-5 fw-bold">Features</h2>
        </Col>
      </Row>
      
      <Row className="g-4 mb-5">
        <Col md={6}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Body className="d-flex">
              <div className="flex-shrink-0 me-3">
                <div className="d-flex align-items-center justify-content-center bg-primary text-white rounded" 
                     style={{ width: '48px', height: '48px' }}>
                  <FileSearch size={24} />
                </div>
              </div>
              <div>
                <Card.Title className="h5 mb-2">Multi-Ecosystem Support</Card.Title>
                <Card.Text className="text-muted">
                  Scans Python (pip, poetry, pipenv) and JavaScript (npm, yarn) projects
                  with full transitive dependency resolution.
                </Card.Text>
              </div>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={6}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Body className="d-flex">
              <div className="flex-shrink-0 me-3">
                <div className="d-flex align-items-center justify-content-center bg-primary text-white rounded" 
                     style={{ width: '48px', height: '48px' }}>
                  <Shield size={24} />
                </div>
              </div>
              <div>
                <Card.Title className="h5 mb-2">OSV.dev Integration</Card.Title>
                <Card.Text className="text-muted">
                  Uses Google's Open Source Vulnerabilities database for comprehensive
                  and up-to-date vulnerability information.
                </Card.Text>
              </div>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={6}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Body className="d-flex">
              <div className="flex-shrink-0 me-3">
                <div className="d-flex align-items-center justify-content-center bg-primary text-white rounded" 
                     style={{ width: '48px', height: '48px' }}>
                  <Zap size={24} />
                </div>
              </div>
              <div>
                <Card.Title className="h5 mb-2">Fast & Efficient</Card.Title>
                <Card.Text className="text-muted">
                  Batched API calls, intelligent caching, and deduplication ensure
                  fast scan times even for large dependency trees.
                </Card.Text>
              </div>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={6}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Body className="d-flex">
              <div className="flex-shrink-0 me-3">
                <div className="d-flex align-items-center justify-content-center bg-primary text-white rounded" 
                     style={{ width: '48px', height: '48px' }}>
                  <Download size={24} />
                </div>
              </div>
              <div>
                <Card.Title className="h5 mb-2">Multiple Export Formats</Card.Title>
                <Card.Text className="text-muted">
                  Export scan results as JSON or CSV for integration with your
                  existing security workflows and tools.
                </Card.Text>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* Getting Started */}
      <Card className="border-0 shadow-sm">
        <Card.Body className="p-5">
          <Row className="text-center mb-4">
            <Col>
              <h2 className="display-6 fw-bold mb-3">Getting Started</h2>
              <p className="lead text-muted mb-4">
                Ready to scan your project? Upload your dependency files or provide a repository path.
              </p>
            </Col>
          </Row>
        
        <Row className="g-4">
          <Col md={4}>
            <Card className="text-center h-100 border-0 shadow-sm">
              <Card.Body>
                <div className="mb-3">
                  <span className="badge bg-primary rounded-circle p-2 fs-5">1</span>
                </div>
                <Card.Title className="h5">Upload Files</Card.Title>
                <Card.Text className="text-muted">
                  Upload your package.json, requirements.txt, or lockfiles
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>
          
          <Col md={4}>
            <Card className="text-center h-100 border-0 shadow-sm">
              <Card.Body>
                <div className="mb-3">
                  <span className="badge bg-primary rounded-circle p-2 fs-5">2</span>
                </div>
                <Card.Title className="h5">Start Scan</Card.Title>
                <Card.Text className="text-muted">
                  Our scanner will analyze all dependencies for vulnerabilities
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>
          
          <Col md={4}>
            <Card className="text-center h-100 border-0 shadow-sm">
              <Card.Body>
                <div className="mb-3">
                  <span className="badge bg-primary rounded-circle p-2 fs-5">3</span>
                </div>
                <Card.Title className="h5">Review Results</Card.Title>
                <Card.Text className="text-muted">
                  Get detailed reports with severity levels and fix recommendations
                </Card.Text>
              </Card.Body>
            </Card>
          </Col>
        </Row>
        </Card.Body>
      </Card>
    </Container>
  );
};

export default HomePage;
