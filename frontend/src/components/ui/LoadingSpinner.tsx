import React from 'react';
import { Spinner, SpinnerProps } from 'react-bootstrap';

interface LoadingSpinnerProps extends SpinnerProps {
  message?: string;
  center?: boolean;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  message,
  center = true,
  size = 'sm',
  variant = 'primary',
  className = '',
  ...props 
}) => {
  const spinnerElement = (
    <div className={`d-flex align-items-center ${className}`}>
      <Spinner 
        animation="border" 
        size={size} 
        variant={variant}
        {...props}
      />
      {message && <span className="ms-2">{message}</span>}
    </div>
  );

  if (center) {
    return (
      <div className="d-flex justify-content-center align-items-center p-4">
        {spinnerElement}
      </div>
    );
  }

  return spinnerElement;
};

export default LoadingSpinner;