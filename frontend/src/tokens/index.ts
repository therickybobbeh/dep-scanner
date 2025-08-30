/**
 * Design Tokens - Single Source of Truth for Design System
 * Following 2025 best practices for token-driven design systems
 */

// Base Tokens - Raw design values
export const baseTokens = {
  // Color Palette
  colors: {
    // Purple Brand Colors
    purple: {
      50: '#faf5ff',
      100: '#f3e8ff', 
      200: '#e9d5ff',
      300: '#d8b4fe',
      400: '#c084fc',
      500: '#a855f7', // Primary
      600: '#9333ea',
      700: '#7c3aed', // Primary Dark
      800: '#6b21a8',
      900: '#581c87',
    },
    // Neutral Grays
    gray: {
      50: '#f9fafb',
      100: '#f3f4f6',
      200: '#e5e7eb',
      300: '#d1d5db',
      400: '#9ca3af',
      500: '#6b7280',
      600: '#4b5563',
      700: '#374151',
      800: '#1f2937',
      900: '#111827',
    },
    // Semantic Colors
    success: {
      50: '#f0fdf4',
      500: '#10b981',
      600: '#059669',
    },
    warning: {
      50: '#fefbeb',
      500: '#f59e0b',
      600: '#d97706',
    },
    danger: {
      50: '#fef2f2',
      500: '#ef4444',
      600: '#dc2626',
    },
    info: {
      50: '#eff6ff',
      500: '#0891b2',
      600: '#0e7490',
    },
  },
  
  // Typography Scale
  typography: {
    fontFamily: {
      sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      mono: ['SF Mono', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
    },
    fontSize: {
      xs: '0.75rem',      // 12px
      sm: '0.875rem',     // 14px  
      base: '1rem',       // 16px
      lg: '1.125rem',     // 18px
      xl: '1.25rem',      // 20px
      '2xl': '1.5rem',    // 24px
      '3xl': '1.875rem',  // 30px
      '4xl': '2.25rem',   // 36px
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    lineHeight: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.6,
    },
  },
  
  // Spacing Scale (based on 4px grid)
  spacing: {
    0: '0',
    1: '0.25rem',   // 4px
    2: '0.5rem',    // 8px
    3: '0.75rem',   // 12px
    4: '1rem',      // 16px
    5: '1.25rem',   // 20px
    6: '1.5rem',    // 24px
    8: '2rem',      // 32px
    10: '2.5rem',   // 40px
    12: '3rem',     // 48px
    16: '4rem',     // 64px
    20: '5rem',     // 80px
  },
  
  // Border Radius Scale
  borderRadius: {
    none: '0',
    sm: '0.25rem',   // 4px
    md: '0.375rem',  // 6px
    lg: '0.5rem',    // 8px
    xl: '0.75rem',   // 12px
    '2xl': '1rem',   // 16px
    full: '9999px',
  },
  
  // Shadow Scale
  boxShadow: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    lg: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    xl: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  },
  
  // Breakpoints
  breakpoints: {
    sm: '576px',
    md: '768px', 
    lg: '992px',
    xl: '1200px',
    '2xl': '1400px',
  },
} as const;

// Semantic Tokens - Contextual meanings mapped to base tokens
export const semanticTokens = {
  colors: {
    // Background Colors
    background: {
      primary: baseTokens.colors.gray[50],
      secondary: baseTokens.colors.gray[200], // Changed from 100 to 200 for better visibility
      elevated: '#ffffff',
      brand: baseTokens.colors.purple[50],
    },
    
    // Text Colors  
    text: {
      primary: baseTokens.colors.gray[800],
      secondary: baseTokens.colors.gray[600],
      muted: baseTokens.colors.gray[500],
      inverse: '#ffffff',
      brand: baseTokens.colors.purple[700],
    },
    
    // Border Colors
    border: {
      primary: baseTokens.colors.gray[200],
      secondary: baseTokens.colors.gray[300],
      brand: baseTokens.colors.purple[200],
    },
    
    // Interactive Colors
    interactive: {
      primary: baseTokens.colors.purple[700],
      primaryHover: baseTokens.colors.purple[800],
      secondary: baseTokens.colors.gray[100],
      secondaryHover: baseTokens.colors.gray[200],
    },
    
    // Status Colors
    status: {
      success: baseTokens.colors.success[500],
      warning: baseTokens.colors.warning[500], 
      danger: baseTokens.colors.danger[500],
      info: baseTokens.colors.info[500],
    },
    
    // Severity Colors (for vulnerability display)
    severity: {
      critical: baseTokens.colors.danger[500],
      high: '#f97316', // orange-500
      medium: baseTokens.colors.warning[500],
      low: baseTokens.colors.success[500],
      unknown: baseTokens.colors.gray[500],
    },
  },
} as const;

// Component Tokens - Specific to UI components
export const componentTokens = {
  button: {
    borderRadius: baseTokens.borderRadius.lg,
    fontWeight: baseTokens.typography.fontWeight.medium,
    padding: {
      sm: `${baseTokens.spacing[2]} ${baseTokens.spacing[3]}`,
      md: `${baseTokens.spacing[3]} ${baseTokens.spacing[4]}`,
      lg: `${baseTokens.spacing[4]} ${baseTokens.spacing[6]}`,
    },
  },
  
  card: {
    borderRadius: baseTokens.borderRadius['2xl'],
    boxShadow: baseTokens.boxShadow.md,
    boxShadowHover: baseTokens.boxShadow.lg,
    padding: baseTokens.spacing[6],
    background: semanticTokens.colors.background.elevated,
    border: `1px solid ${semanticTokens.colors.border.primary}`,
  },
  
  input: {
    borderRadius: baseTokens.borderRadius.lg,
    border: `1px solid ${semanticTokens.colors.border.secondary}`,
    padding: `${baseTokens.spacing[3]} ${baseTokens.spacing[4]}`,
    fontSize: baseTokens.typography.fontSize.base,
  },
  
  badge: {
    borderRadius: baseTokens.borderRadius.md,
    fontSize: baseTokens.typography.fontSize.xs,
    fontWeight: baseTokens.typography.fontWeight.medium,
    padding: `${baseTokens.spacing[1]} ${baseTokens.spacing[2]}`,
  },
  
  table: {
    borderColor: semanticTokens.colors.border.primary,
    headerBackground: semanticTokens.colors.background.secondary,
    stripedBackground: semanticTokens.colors.background.secondary,
    hoverBackground: baseTokens.colors.purple[50],
  },
} as const;

// Export all tokens as a single object for easy access
export const tokens = {
  base: baseTokens,
  semantic: semanticTokens,
  component: componentTokens,
} as const;

// Type exports for TypeScript support
export type BaseTokens = typeof baseTokens;
export type SemanticTokens = typeof semanticTokens;
export type ComponentTokens = typeof componentTokens;
export type Tokens = typeof tokens;