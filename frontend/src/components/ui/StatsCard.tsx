import React from 'react';
import { Card, CardProps } from 'react-bootstrap';
import { useToken } from '../../providers/ThemeProvider';

interface StatsCardProps extends CardProps {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  variant?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'secondary';
  subtitle?: string;
  trend?: {
    value: number;
    isPositive: boolean;
    label: string;
  };
}

const StatsCard: React.FC<StatsCardProps> = ({ 
  title,
  value,
  icon,
  variant = 'primary',
  subtitle,
  trend,
  className = '',
  ...props 
}) => {
  const { tokens } = useToken();
  
  // Get semantic colors for better consistency
  const getBorderStyle = () => {
    const borderWidth = '4px';
    switch (variant) {
      case 'primary':
        return { borderLeftColor: tokens.semantic.colors.interactive.primary, borderLeftWidth: borderWidth };
      case 'danger':
        return { borderLeftColor: tokens.semantic.colors.status.danger, borderLeftWidth: borderWidth };
      case 'success':
        return { borderLeftColor: tokens.semantic.colors.status.success, borderLeftWidth: borderWidth };
      case 'warning':
        return { borderLeftColor: tokens.semantic.colors.status.warning, borderLeftWidth: borderWidth };
      case 'info':
        return { borderLeftColor: tokens.semantic.colors.status.info, borderLeftWidth: borderWidth };
      default:
        return { borderLeftColor: tokens.semantic.colors.text.secondary, borderLeftWidth: borderWidth };
    }
  };

  return (
    <Card 
      className={`h-100 ${className}`} 
      style={{
        borderRadius: tokens.component.card.borderRadius,
        boxShadow: tokens.component.card.boxShadow,
        transition: 'all 0.15s ease',
        backgroundColor: tokens.component.card.background,
        border: tokens.component.card.border,
        ...getBorderStyle(), // Apply after border to override
      }} 
      {...props}
    >
      <Card.Body>
        <div className="d-flex justify-content-between align-items-start">
          <div className="flex-grow-1">
            <div 
              className="small text-uppercase fw-bold"
              style={{ 
                color: tokens.semantic.colors.text.secondary,
                fontSize: tokens.base.typography.fontSize.xs,
                fontWeight: tokens.base.typography.fontWeight.bold,
              }}
            >
              {title}
            </div>
            <div 
              className="mb-1 fw-bold"
              style={{
                fontSize: tokens.base.typography.fontSize['2xl'],
                fontWeight: tokens.base.typography.fontWeight.bold,
                color: tokens.semantic.colors.text.primary,
              }}
            >
              {value}
            </div>
            {subtitle && (
              <div 
                className="small"
                style={{ 
                  color: tokens.semantic.colors.text.muted,
                  fontSize: tokens.base.typography.fontSize.sm,
                }}
              >
                {subtitle}
              </div>
            )}
            {trend && (
              <div className={`small mt-1 ${trend.isPositive ? 'text-success' : 'text-danger'}`}>
                <span>{trend.isPositive ? '↑' : '↓'}</span>
                <span className="ms-1">{Math.abs(trend.value)}% {trend.label}</span>
              </div>
            )}
          </div>
          {icon && (
            <div 
              style={{ 
                color: getBorderStyle().borderLeftColor,
                opacity: 0.75,
              }}
            >
              {icon}
            </div>
          )}
        </div>
      </Card.Body>
    </Card>
  );
};

export default StatsCard;
