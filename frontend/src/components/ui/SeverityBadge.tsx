import React from 'react';
import { Badge, BadgeProps } from 'react-bootstrap';
import { SeverityLevel } from '../../types/common';
import { getSeverityVariant } from '../../utils/severity';

interface SeverityBadgeProps extends Omit<BadgeProps, 'bg'> {
  severity: SeverityLevel | null;
  showIcon?: boolean;
}

const SeverityBadge: React.FC<SeverityBadgeProps> = ({ 
  severity, 
  showIcon = false, 
  className = '', 
  ...props 
}) => {
  const variant = getSeverityVariant(severity);
  const displayText = severity || SeverityLevel.UNKNOWN;
  
  const getIcon = (sev: SeverityLevel | null) => {
    if (!showIcon) return '';
    
    switch (sev) {
      case SeverityLevel.CRITICAL:
        return '🔴 ';
      case SeverityLevel.HIGH:
        return '🟠 ';
      case SeverityLevel.MEDIUM:
        return '🟡 ';
      case SeverityLevel.LOW:
        return '🟢 ';
      default:
        return '⚪ ';
    }
  };

  return (
    <Badge 
      bg={variant}
      className={`text-uppercase ${className}`}
      {...props}
    >
      {getIcon(severity)}{displayText}
    </Badge>
  );
};

export default SeverityBadge;