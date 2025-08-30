/**
 * Unit tests for ThemeProvider component
 */
import { render, screen, act } from '@testing-library/react'
import { ThemeProvider, useTheme, useToken } from '../ThemeProvider'
import { tokens } from '../../tokens'

// Test component that uses the theme context
const TestComponent = () => {
  const { currentTheme, setTheme, availableThemes } = useTheme()
  const { getColor, getSemanticColor } = useToken()
  
  return (
    <div>
      <div data-testid="current-theme">{currentTheme}</div>
      <div data-testid="available-themes">{availableThemes.join(',')}</div>
      <div data-testid="primary-color">{getColor('purple.700')}</div>
      <div data-testid="semantic-color">{getSemanticColor('interactive', 'primary')}</div>
      <button onClick={() => setTheme('light')} data-testid="set-light-theme">
        Set Light Theme
      </button>
    </div>
  )
}

describe('ThemeProvider', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    
    // Reset any CSS variables that might have been set
    const root = document.documentElement
    root.style.removeProperty('--semantic-interactive-primary')
    root.style.removeProperty('--color-purple-700')
  })

  it('provides default light theme', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    expect(screen.getByTestId('current-theme')).toHaveTextContent('light')
    expect(screen.getByTestId('available-themes')).toHaveTextContent('light')
  })

  it('provides access to design tokens', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    expect(screen.getByTestId('primary-color')).toHaveTextContent(tokens.base.colors.purple[700])
    expect(screen.getByTestId('semantic-color')).toHaveTextContent(tokens.semantic.colors.interactive.primary)
  })

  it('applies CSS variables to document root', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    const root = document.documentElement
    const primaryColor = root.style.getPropertyValue('--semantic-interactive-primary')
    const purpleColor = root.style.getPropertyValue('--color-purple-700')
    
    expect(primaryColor).toBe(tokens.semantic.colors.interactive.primary)
    expect(purpleColor).toBe(tokens.base.colors.purple[700])
  })

  it('allows theme switching', () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    expect(screen.getByTestId('current-theme')).toHaveTextContent('light')
    
    act(() => {
      screen.getByTestId('set-light-theme').click()
    })

    expect(screen.getByTestId('current-theme')).toHaveTextContent('light')
  })

  it('loads theme from localStorage', () => {
    localStorage.setItem('theme', 'light')
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    expect(screen.getByTestId('current-theme')).toHaveTextContent('light')
  })

  it('falls back to default theme for invalid localStorage value', () => {
    localStorage.setItem('theme', 'invalid-theme')
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    )

    expect(screen.getByTestId('current-theme')).toHaveTextContent('light')
  })

  it('accepts custom default theme', () => {
    render(
      <ThemeProvider defaultTheme="light">
        <TestComponent />
      </ThemeProvider>
    )

    expect(screen.getByTestId('current-theme')).toHaveTextContent('light')
  })

  it('throws error when useTheme is used outside provider', () => {
    // Suppress console.error for this test
    const originalError = console.error
    console.error = vi.fn()

    expect(() => {
      render(<TestComponent />)
    }).toThrow('useTheme must be used within a ThemeProvider')

    console.error = originalError
  })
})

describe('useToken hook', () => {
  const TokenTestComponent = () => {
    const { getSpacing, getFontSize, tokens } = useToken()
    
    return (
      <div>
        <div data-testid="spacing-4">{getSpacing('4')}</div>
        <div data-testid="font-lg">{getFontSize('lg')}</div>
        <div data-testid="tokens-available">{tokens ? 'available' : 'unavailable'}</div>
      </div>
    )
  }

  it('provides utility functions for token access', () => {
    render(
      <ThemeProvider>
        <TokenTestComponent />
      </ThemeProvider>
    )

    expect(screen.getByTestId('spacing-4')).toHaveTextContent(tokens.base.spacing[4])
    expect(screen.getByTestId('font-lg')).toHaveTextContent(tokens.base.typography.fontSize.lg)
    expect(screen.getByTestId('tokens-available')).toHaveTextContent('available')
  })
})