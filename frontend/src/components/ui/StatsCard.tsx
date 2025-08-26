import React from 'react';
import { Card, CardProps } from 'react-bootstrap';

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
  const borderColor = `border-${variant}`;

  return (
    <Card className={`h-100 ${borderColor} ${className}`} style={{ borderLeftWidth: '4px' }} {...props}>
      <Card.Body>
        <div className="d-flex justify-content-between align-items-start">
          <div className="flex-grow-1">
            <div className="text-muted small text-uppercase fw-bold">{title}</div>
            <div className="h4 mb-1 fw-bold">{value}</div>
            {subtitle && <div className="text-muted small">{subtitle}</div>}
            {trend && (
              <div className={`small mt-1 ${trend.isPositive ? 'text-success' : 'text-danger'}`}>
                <span>{trend.isPositive ? '↑' : '↓'}</span>
                <span className="ms-1">{Math.abs(trend.value)}% {trend.label}</span>
              </div>
            )}
          </div>
          {icon && (
            <div className={`text-${variant} opacity-75`}>
              {icon}
            </div>
          )}
        </div>
      </Card.Body>
    </Card>
  );
};

export default StatsCard;
