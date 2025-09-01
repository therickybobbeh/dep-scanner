import React, { useState, useEffect } from 'react';
import { Modal, Button, Alert, Badge } from 'react-bootstrap';
import { RotateCcw } from 'lucide-react';
import NewtonsCradleLoader from './NewtonsCradleLoader';
import api from '../../utils/api';
import type { ScanRequest } from '../../types/api';

interface ScanLoadingModalProps {
  show: boolean;
  onHide: () => void;
  onSuccess: (jobId: string) => void;
  scanRequest: ScanRequest;
}

const ScanLoadingModal: React.FC<ScanLoadingModalProps> = ({
  show,
  onHide,
  onSuccess,
  scanRequest
}) => {
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('Preparing scan...');
  const [jobId, setJobId] = useState<string | null>(null);

  const performScan = async () => {
    try {
      setIsScanning(true);
      setError(null);
      setProgress(5);
      setCurrentStep('Starting scan...');
      
      // Start the scan
      const response = await api.post('/scan', scanRequest);
      const { job_id } = response.data;
      setJobId(job_id);
      
      setCurrentStep('Scan started, monitoring progress...');
      setProgress(10);
      
      // Poll for status updates
      await pollScanStatus(job_id);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start scan');
      setIsScanning(false);
    }
  };

  const pollScanStatus = async (jobId: string) => {
    const pollInterval = 1000; // Poll every second
    const maxAttempts = 300; // Maximum 5 minutes
    let attempts = 0;

    const poll = async () => {
      try {
        attempts++;
        
        const response = await api.get(`/status/${jobId}`);
        const status = response.data;
        
        // Update progress
        setProgress(status.progress_percent || 0);
        setCurrentStep(status.current_step || 'Processing...');
        
        if (status.status === 'completed') {
          // Scan completed successfully
          setIsScanning(false);
          setCurrentStep('Scan completed! Redirecting to results...');
          setProgress(100);
          
          // Small delay to show completion message
          setTimeout(() => {
            onSuccess(jobId);
          }, 500);
          
        } else if (status.status === 'failed') {
          // Scan failed
          throw new Error(status.error_message || 'Scan failed');
          
        } else if (status.status === 'running' || status.status === 'pending') {
          // Still processing, continue polling
          if (attempts < maxAttempts) {
            setTimeout(poll, pollInterval);
          } else {
            throw new Error('Scan timeout - took longer than expected');
          }
        }
        
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to get scan status');
        setIsScanning(false);
      }
    };
    
    // Start polling
    setTimeout(poll, pollInterval);
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    await performScan();
    setIsRetrying(false);
  };

  const handleModalClose = () => {
    if (isScanning) {
      // Show confirmation dialog when trying to close during scan
      const confirmed = window.confirm(
        'A security scan is currently in progress. Are you sure you want to cancel it? This will interrupt the scan and you\'ll lose your progress.'
      );
      if (confirmed) {
        onHide();
      }
    } else {
      // Allow normal closing when not scanning
      onHide();
    }
  };

  // Start scan when modal opens
  useEffect(() => {
    if (show && !error) {
      performScan();
    }
  }, [show]);

  // Reset state when modal closes
  useEffect(() => {
    if (!show) {
      setIsScanning(false);
      setError(null);
      setIsRetrying(false);
      setProgress(0);
      setCurrentStep('Preparing scan...');
      setJobId(null);
    }
  }, [show]);

  // Prevent browser exit during scan
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isScanning) {
        e.preventDefault();
        e.returnValue = 'A security scan is currently in progress. Are you sure you want to leave? This will interrupt the scan.';
        return e.returnValue;
      }
    };

    // Add event listener when scanning starts
    if (isScanning) {
      window.addEventListener('beforeunload', handleBeforeUnload);
    }

    // Cleanup event listener
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [isScanning]);

  return (
    <Modal
      show={show}
      onHide={handleModalClose} // Use custom close handler with confirmation
      centered
      backdrop={isScanning ? 'static' : true} // Prevent backdrop click during scan
      keyboard={!isScanning} // Disable ESC key during scan
      size="lg"
      className="scan-loading-modal"
    >
      <Modal.Header closeButton={!isScanning}>
        <Modal.Title className="d-flex align-items-center">
          {error ? (
            <span className="text-danger">Scan Failed</span>
          ) : isScanning ? (
            <span>
              Security Scan in Progress 
              <Badge bg="warning" className="ms-2 small">Exit Blocked</Badge>
            </span>
          ) : (
            <span>Ready to Scan</span>
          )}
        </Modal.Title>
      </Modal.Header>

      <Modal.Body className="text-center py-4">
        {error ? (
          <Alert variant="danger" className="mb-4">
            <Alert.Heading>Something went wrong</Alert.Heading>
            <p className="mb-3">{error}</p>
            <div className="d-flex gap-2 justify-content-center">
              <Button 
                variant="outline-danger" 
                size="sm" 
                onClick={handleRetry}
                disabled={isRetrying}
              >
                <RotateCcw size={16} className="me-1" />
                {isRetrying ? 'Retrying...' : 'Try Again'}
              </Button>
              <Button 
                variant="secondary" 
                size="sm" 
                onClick={onHide}
              >
                Cancel
              </Button>
            </div>
          </Alert>
        ) : isScanning ? (
          <>
            <NewtonsCradleLoader 
              message="🛡️ Scanning for vulnerabilities..."
              className="mb-4"
            />
            
            {/* Progress bar */}
            <div className="mb-3">
              <div className="progress mb-2" style={{ height: '8px' }}>
                <div 
                  className="progress-bar progress-bar-striped progress-bar-animated" 
                  role="progressbar" 
                  style={{ width: `${progress}%` }}
                  aria-valuenow={progress}
                  aria-valuemin={0}
                  aria-valuemax={100}
                ></div>
              </div>
              <small className="text-muted">
                {Math.round(progress)}% - {currentStep}
              </small>
            </div>

            {jobId && (
              <small className="text-muted d-block mb-2">
                Job ID: <code>{jobId}</code>
              </small>
            )}
            
            <div className="text-muted small">
              <div className="mb-1">
                This may take a few minutes depending on the number of dependencies
              </div>
              <div className="text-warning">
                ⚠️ Please don't close this window or navigate away during the scan
              </div>
            </div>
          </>
        ) : (
          <>
            <NewtonsCradleLoader 
              message="🛡️ Preparing to scan..."
              className="mb-4"
            />
            
            <small className="text-muted d-block">
              Getting ready to analyze your dependencies for security vulnerabilities
            </small>
          </>
        )}
      </Modal.Body>
    </Modal>
  );
};

export default ScanLoadingModal;