import React from 'react';
import { ProgressBar as BSProgressBar, ProgressBarProps } from 'react-bootstrap';

interface CustomProgressBarProps extends Omit<ProgressBarProps, 'now'> {
  value: number;
  showLabel?: boolean;
  animate?: boolean;
  height?: string;
}

const ProgressBar: React.FC<CustomProgressBarProps> = ({ 
  value,
  showLabel = true,
  animate = true,
  height = '1rem',
  variant = 'primary',
  className = '',
  style = {},
  ...props 
}) => {
  const progressStyle = {
    height,
    ...style,
  };

  return (
    <BSProgressBar
      now={Math.min(100, Math.max(0, value))}
      animated={animate}
      variant={variant}
      style={progressStyle}
      className={className}
      label={showLabel ? `${Math.round(value)}%` : undefined}
      {...props}
    />
  );
};

export default ProgressBar;