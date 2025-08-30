import React from 'react';
import { Badge, BadgeProps } from 'react-bootstrap';
import { SeverityLevel } from '../../types/common';
import { useToken } from '../../providers/ThemeProvider';

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
  const { tokens } = useToken();
  const displayText = severity || SeverityLevel.UNKNOWN;
  
  // Get severity color from design tokens
  const getSeverityColor = (sev: SeverityLevel | null): { bg: string; color: string } => {
    switch (sev) {
      case SeverityLevel.CRITICAL:
        return { bg: tokens.semantic.colors.severity.critical, color: 'white' };
      case SeverityLevel.HIGH:
        return { bg: tokens.semantic.colors.severity.high, color: 'white' };
      case SeverityLevel.MEDIUM:
        return { bg: tokens.semantic.colors.severity.medium, color: tokens.semantic.colors.text.primary };
      case SeverityLevel.LOW:
        return { bg: tokens.semantic.colors.severity.low, color: 'white' };
      default:
        return { bg: tokens.semantic.colors.severity.unknown, color: 'white' };
    }
  };
  
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

  const severityColors = getSeverityColor(severity);
  
  return (
    <Badge 
      className={`text-uppercase ${className}`}
      style={{
        backgroundColor: severityColors.bg,
        color: severityColors.color,
        borderRadius: tokens.component.badge.borderRadius,
        fontSize: tokens.component.badge.fontSize,
        fontWeight: tokens.component.badge.fontWeight,
        padding: tokens.component.badge.padding,
        border: 'none',
      }}
      {...props}
    >
      {getIcon(severity)}{displayText}
    </Badge>
  );
};

export default SeverityBadge;