import React from 'react';
import { Modal, Button, Card, Badge } from 'react-bootstrap';
import { FileText, Play, Download, AlertTriangle } from 'lucide-react';
import samplePackageLock from '../../data/samplePackageLock.json';

interface SampleFileModalProps {
  show: boolean;
  onHide: () => void;
  onTestSample: () => void;
}

const SampleFileModal: React.FC<SampleFileModalProps> = ({
  show,
  onHide,
  onTestSample
}) => {
  const sampleContent = `{
  "name": "demo-vulnerable-app",
  "version": "1.0.0",
  "lockfileVersion": 2,
  "requires": true,
  "packages": {
    "": {
      "name": "demo-vulnerable-app",
      "version": "1.0.0",
      "dependencies": {
        "axios": "0.19.0",           // ⚠️ Multiple SSRF vulnerabilities
        "lodash": "4.17.11",         // ⚠️ Prototype pollution
        "next": "12.0.0",            // ⚠️ XSS & security issues
        "react": "17.0.0",           // ⚠️ Outdated with known issues
        "minimist": "1.2.0",         // ⚠️ Prototype pollution
        "node-fetch": "1.7.3",       // ⚠️ Outdated, security issues
        "handlebars": "4.0.0"        // ⚠️ Template injection
      }
    },
    "node_modules/axios": {
      "version": "0.19.0",
      "resolved": "https://registry.npmjs.org/axios/-/axios-0.19.0.tgz",
      "dependencies": {
        "follow-redirects": "1.5.10"  // ⚠️ Open redirect vulnerability
      }
    },
    "node_modules/lodash": {
      "version": "4.17.11",
      "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.11.tgz"
    }
    // ... (145+ more dependencies with various vulnerabilities)
  },
  "dependencies": {
    // Full dependency tree with exact versions and integrity hashes
    // This file will reveal ~15-25 vulnerabilities when scanned
  }
}`;

  const downloadSample = () => {
    // Download the actual full sample file instead of the truncated version
    const fullSampleContent = JSON.stringify(samplePackageLock, null, 2);
    const blob = new Blob([fullSampleContent], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sample-package-lock.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Modal
      show={show}
      onHide={onHide}
      size="lg"
      centered
      className="sample-file-modal"
    >
      <Modal.Header closeButton>
        <Modal.Title className="d-flex align-items-center">
          <FileText size={24} className="me-2 text-primary" />
          Sample package-lock.json File
          <Badge bg="warning" className="ms-2">Demo</Badge>
        </Modal.Title>
      </Modal.Header>

      <Modal.Body>
        <Card className="mb-3">
          <Card.Body className="py-3">
            <div className="d-flex align-items-start">
              <AlertTriangle size={20} className="text-warning me-2 mt-1 flex-shrink-0" />
              <div>
                <strong className="text-warning">Vulnerable Demo Project</strong>
                <p className="mb-0 small text-muted">
                  This sample file contains intentionally outdated packages with known vulnerabilities for demonstration purposes.
                  It includes popular packages like axios, lodash, and next.js with older versions.
                </p>
              </div>
            </div>
          </Card.Body>
        </Card>

        <div className="mb-3">
          <h6 className="mb-2">🎯 What you'll find:</h6>
          <ul className="small text-muted mb-0">
            <li><strong>7 direct dependencies</strong> with various vulnerability levels</li>
            <li><strong>Multiple CVEs</strong> including SSRF, prototype pollution, and more</li>
            <li><strong>Real vulnerability data</strong> from the OSV database</li>
            <li><strong>Complete dependency tree</strong> with transitive vulnerabilities</li>
          </ul>
        </div>

        <Card className="bg-light">
          <Card.Header className="py-2">
            <small className="text-muted font-monospace">
              📁 sample-package-lock.json
            </small>
          </Card.Header>
          <Card.Body style={{ maxHeight: '300px', overflowY: 'auto' }}>
            <pre className="mb-0" style={{ fontSize: '0.8rem', lineHeight: '1.4' }}>
              <code>{sampleContent}</code>
            </pre>
          </Card.Body>
        </Card>
      </Modal.Body>

      <Modal.Footer className="d-flex justify-content-between">
        <Button 
          variant="outline-secondary" 
          onClick={downloadSample}
          size="sm"
        >
          <Download size={16} className="me-1" />
          Download Sample
        </Button>
        
        <div>
          <Button variant="secondary" onClick={onHide} className="me-2">
            Close
          </Button>
          <Button 
            variant="primary" 
            onClick={() => {
              onTestSample();
              onHide();
            }}
          >
            <Play size={16} className="me-1" />
            Test This Sample
          </Button>
        </div>
      </Modal.Footer>
    </Modal>
  );
};

export default SampleFileModal;