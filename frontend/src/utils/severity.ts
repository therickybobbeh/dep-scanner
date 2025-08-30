import { SeverityLevel } from '../types/common';

/**
 * Severity utility functions
 */

export const severityColors: Record<SeverityLevel, string> = {
  [SeverityLevel.CRITICAL]: '#dc3545', // Bootstrap danger
  [SeverityLevel.HIGH]: '#fd7e14',     // Bootstrap warning
  [SeverityLevel.MEDIUM]: '#ffc107',   // Bootstrap warning
  [SeverityLevel.LOW]: '#28a745',      // Bootstrap success  
  [SeverityLevel.UNKNOWN]: '#6c757d'   // Bootstrap secondary
};

export const severityBootstrapVariants: Record<SeverityLevel, string> = {
  [SeverityLevel.CRITICAL]: 'danger',
  [SeverityLevel.HIGH]: 'warning',
  [SeverityLevel.MEDIUM]: 'warning',
  [SeverityLevel.LOW]: 'success',
  [SeverityLevel.UNKNOWN]: 'secondary'
};

export const severityPriority: Record<SeverityLevel, number> = {
  [SeverityLevel.CRITICAL]: 5,
  [SeverityLevel.HIGH]: 4,
  [SeverityLevel.MEDIUM]: 3,
  [SeverityLevel.LOW]: 2,
  [SeverityLevel.UNKNOWN]: 1
};

export function getSeverityColor(severity: SeverityLevel | null): string {
  return severity ? severityColors[severity] : severityColors[SeverityLevel.UNKNOWN];
}

export function getSeverityVariant(severity: SeverityLevel | null): string {
  return severity ? severityBootstrapVariants[severity] : severityBootstrapVariants[SeverityLevel.UNKNOWN];
}

export function sortBySeverity(vulnerabilities: any[]): any[] {
  return [...vulnerabilities].sort((a, b) => {
    // Normalize severity strings for consistent comparison
    const severityA = a.severity?.toUpperCase() as SeverityLevel;
    const severityB = b.severity?.toUpperCase() as SeverityLevel;
    
    const priorityA = severityA && Object.values(SeverityLevel).includes(severityA) 
      ? severityPriority[severityA] 
      : 0;
    const priorityB = severityB && Object.values(SeverityLevel).includes(severityB) 
      ? severityPriority[severityB] 
      : 0;
    
    return priorityB - priorityA; // Descending order (highest severity first)
  });
}

export function groupBySeverity(vulnerabilities: any[]): Record<SeverityLevel, any[]> {
  const groups: Record<SeverityLevel, any[]> = {
    [SeverityLevel.CRITICAL]: [],
    [SeverityLevel.HIGH]: [],
    [SeverityLevel.MEDIUM]: [],
    [SeverityLevel.LOW]: [],
    [SeverityLevel.UNKNOWN]: []
  };

  vulnerabilities.forEach(vuln => {
    // Normalize severity string to enum value (case-insensitive)
    const severityStr = vuln.severity?.toUpperCase();
    let severity: SeverityLevel = SeverityLevel.UNKNOWN;
    
    if (severityStr && Object.values(SeverityLevel).includes(severityStr as SeverityLevel)) {
      severity = severityStr as SeverityLevel;
    }
    
    groups[severity].push(vuln);
  });

  return groups;
}