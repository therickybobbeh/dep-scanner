/**
 * Theme Provider - Centralized theme management using React Context
 * Provides design tokens to all components following 2025 best practices
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { tokens, type Tokens } from '../tokens';

// Theme configuration type
interface ThemeConfig {
  name: string;
  tokens: Tokens;
}

// Available themes
const themes: Record<string, ThemeConfig> = {
  light: {
    name: 'Light',
    tokens,
  },
  // Future themes can be added here (dark, high-contrast, etc.)
};

// Theme context type
interface ThemeContextType {
  currentTheme: string;
  themeConfig: ThemeConfig;
  setTheme: (themeName: string) => void;
  availableThemes: string[];
  tokens: Tokens;
}

// Create theme context
const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// Theme provider props
interface ThemeProviderProps {
  children: React.ReactNode;
  defaultTheme?: string;
}

// CSS variable generator - converts tokens to CSS custom properties
const generateCSSVariables = (tokens: Tokens): Record<string, string> => {
  const cssVars: Record<string, string> = {};
  
  // Base color tokens
  Object.entries(tokens.base.colors).forEach(([colorName, colorScale]) => {
    if (typeof colorScale === 'object') {
      Object.entries(colorScale).forEach(([shade, value]) => {
        cssVars[`--color-${colorName}-${shade}`] = value;
      });
    } else {
      cssVars[`--color-${colorName}`] = colorScale;
    }
  });
  
  // Typography tokens
  Object.entries(tokens.base.typography.fontSize).forEach(([size, value]) => {
    cssVars[`--font-size-${size}`] = value;
  });
  
  Object.entries(tokens.base.typography.fontWeight).forEach(([weight, value]) => {
    cssVars[`--font-weight-${weight}`] = value.toString();
  });
  
  Object.entries(tokens.base.typography.lineHeight).forEach(([height, value]) => {
    cssVars[`--line-height-${height}`] = value.toString();
  });
  
  // Spacing tokens
  Object.entries(tokens.base.spacing).forEach(([size, value]) => {
    cssVars[`--spacing-${size}`] = value;
  });
  
  // Border radius tokens
  Object.entries(tokens.base.borderRadius).forEach(([size, value]) => {
    cssVars[`--border-radius-${size}`] = value;
  });
  
  // Shadow tokens
  Object.entries(tokens.base.boxShadow).forEach(([size, value]) => {
    cssVars[`--box-shadow-${size}`] = value;
  });
  
  // Semantic color tokens
  Object.entries(tokens.semantic.colors).forEach(([category, colors]) => {
    Object.entries(colors).forEach(([name, value]) => {
      cssVars[`--semantic-${category}-${name}`] = value;
    });
  });
  
  // Bootstrap overrides for existing components
  cssVars['--bs-primary'] = tokens.semantic.colors.interactive.primary;
  cssVars['--bs-primary-rgb'] = '124, 58, 237'; // purple-700 RGB
  cssVars['--bs-secondary'] = tokens.semantic.colors.text.secondary;
  cssVars['--bs-body-bg'] = tokens.semantic.colors.background.primary;
  cssVars['--bs-body-color'] = tokens.semantic.colors.text.primary;
  
  return cssVars;
};

// Apply CSS variables to document root
const applyCSSVariables = (variables: Record<string, string>) => {
  const root = document.documentElement;
  
  Object.entries(variables).forEach(([property, value]) => {
    root.style.setProperty(property, value);
  });
};

// Theme Provider Component
export const ThemeProvider: React.FC<ThemeProviderProps> = ({ 
  children, 
  defaultTheme = 'light' 
}) => {
  const [currentTheme, setCurrentTheme] = useState(defaultTheme);
  
  // Get current theme configuration
  const themeConfig = themes[currentTheme] || themes.light;
  
  // Apply CSS variables when theme changes
  useEffect(() => {
    const cssVariables = generateCSSVariables(themeConfig.tokens);
    applyCSSVariables(cssVariables);
  }, [themeConfig]);
  
  // Theme setter with validation
  const setTheme = (themeName: string) => {
    if (themes[themeName]) {
      setCurrentTheme(themeName);
      
      // Persist theme preference
      try {
        localStorage.setItem('theme', themeName);
      } catch (error) {
        console.warn('Failed to save theme preference:', error);
      }
    }
  };
  
  // Load saved theme preference on mount
  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme && themes[savedTheme]) {
        setCurrentTheme(savedTheme);
      }
    } catch (error) {
      console.warn('Failed to load theme preference:', error);
    }
  }, []);
  
  const contextValue: ThemeContextType = {
    currentTheme,
    themeConfig,
    setTheme,
    availableThemes: Object.keys(themes),
    tokens: themeConfig.tokens,
  };
  
  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
};

// Custom hook for consuming theme context
export const useTheme = () => {
  const context = useContext(ThemeContext);
  
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  
  return context;
};

// Utility hook for getting specific token values
export const useToken = () => {
  const { tokens } = useTheme();
  
  // Helper functions for easy token access
  const getColor = (path: string) => {
    const parts = path.split('.');
    let value: any = tokens.base.colors;
    
    for (const part of parts) {
      value = value?.[part];
    }
    
    return value as string | undefined;
  };
  
  const getSemanticColor = (category: string, name: string) => {
    return (tokens.semantic.colors as any)?.[category]?.[name] as string | undefined;
  };
  
  const getSpacing = (size: string | number) => {
    return tokens.base.spacing[size as keyof typeof tokens.base.spacing];
  };
  
  const getFontSize = (size: string) => {
    return tokens.base.typography.fontSize[size as keyof typeof tokens.base.typography.fontSize];
  };
  
  return {
    tokens,
    getColor,
    getSemanticColor,
    getSpacing,
    getFontSize,
  };
};

export default ThemeProvider;