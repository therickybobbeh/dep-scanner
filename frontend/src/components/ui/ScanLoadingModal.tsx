import React, { useState, useEffect } from 'react';
import { Modal, Button, Alert } from 'react-bootstrap';
import { X, RotateCcw } from 'lucide-react';
import NewtonsCradleLoader from './NewtonsCradleLoader';
import axios from 'axios';
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
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const getProgressMessage = (progress: number): string => {
    if (progress < 15) return "🔧 Initializing security scanner...";
    if (progress < 30) return "📄 Processing your manifest file...";
    if (progress < 60) return "📦 Resolving dependency tree...";
    if (progress < 85) return "🛡️ Querying OSV database - this can take a while...";
    if (progress < 95) return "🔍 Analyzing security vulnerabilities...";
    return "✅ Scan completed! Redirecting to results...";
  };

  const simulateProgress = () => {
    setProgress(0);
    setError(null);
    
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) {
          clearInterval(progressInterval);
          return 90; // Stop at 90% until actual completion
        }
        // Slower progress for OSV database phase (most time-consuming)
        if (prev >= 30 && prev < 85) {
          return prev + Math.random() * 2; // Slower increment
        }
        return prev + Math.random() * 8; // Faster increment for other phases
      });
    }, 500);

    return progressInterval;
  };

  const performScan = async () => {
    try {
      const progressInterval = simulateProgress();
      
      const response = await axios.post('/api/scan', scanRequest);
      const { job_id } = response.data;

      // Complete progress and show success
      clearInterval(progressInterval);
      setProgress(100);
      
      // Brief delay to show completion message
      setTimeout(() => {
        onSuccess(job_id);
      }, 1000);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start scan');
      setProgress(0);
    }
  };

  const handleRetry = async () => {
    setIsRetrying(true);
    await performScan();
    setIsRetrying(false);
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
      setProgress(0);
      setError(null);
      setIsRetrying(false);
    }
  }, [show]);

  return (
    <Modal
      show={show}
      onHide={error ? onHide : undefined} // Only allow close if there's an error
      centered
      backdrop={error ? true : 'static'} // Prevent closing unless error
      keyboard={false}
      size="lg"
      className="scan-loading-modal"
    >
      <Modal.Header className={error ? "border-bottom" : "border-0"}>
        <Modal.Title className="d-flex align-items-center w-100 justify-content-center">
          {error ? (
            <span className="text-danger">Scan Failed</span>
          ) : progress >= 100 ? (
            <span className="text-success">Scan Completed!</span>
          ) : (
            <span>Security Scan in Progress</span>
          )}
        </Modal.Title>
        {error && (
          <Button
            variant="link"
            className="p-0 text-muted"
            onClick={onHide}
            aria-label="Close"
          >
            <X size={20} />
          </Button>
        )}
      </Modal.Header>

      <Modal.Body className="text-center py-5">
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
        ) : (
          <>
            <NewtonsCradleLoader 
              message={getProgressMessage(progress)}
              progress={progress}
              className="mb-4"
            />
            
            <div className="progress mb-3" style={{ height: '8px' }}>
              <div 
                className="progress-bar bg-primary"
                role="progressbar"
                style={{ width: `${Math.min(progress, 100)}%` }}
                aria-valuenow={Math.min(progress, 100)}
                aria-valuemin={0}
                aria-valuemax={100}
              />
            </div>
            
            <small className="text-muted d-block">
              {progress < 30 
                ? "Setting up your security scan..."
                : progress < 85 
                ? "This may take a few minutes depending on the number of dependencies"
                : "Almost finished! Preparing your security report..."
              }
            </small>
            
            {progress >= 100 && (
              <div className="mt-3">
                <small className="text-success">
                  🎉 Redirecting you to the security report in a moment...
                </small>
              </div>
            )}
          </>
        )}
      </Modal.Body>
    </Modal>
  );
};

export default ScanLoadingModal;