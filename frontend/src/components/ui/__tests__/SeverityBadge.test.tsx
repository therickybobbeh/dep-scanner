/**
 * Unit tests for SeverityBadge component
 */
import { render, screen } from '@testing-library/react'
import SeverityBadge from '../SeverityBadge'
import { ThemeProvider } from '../../../providers/ThemeProvider'
import { SeverityLevel } from '../../../types/common'

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider>
      {component}
    </ThemeProvider>
  )
}

describe('SeverityBadge', () => {
  it('renders critical severity with correct styling', () => {
    renderWithTheme(<SeverityBadge severity={SeverityLevel.CRITICAL} />)
    
    const badge = screen.getByText('CRITICAL')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('text-uppercase')
  })

  it('renders high severity with correct styling', () => {
    renderWithTheme(<SeverityBadge severity={SeverityLevel.HIGH} />)
    
    const badge = screen.getByText('HIGH')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('text-uppercase')
  })

  it('renders medium severity with correct styling', () => {
    renderWithTheme(<SeverityBadge severity={SeverityLevel.MEDIUM} />)
    
    const badge = screen.getByText('MEDIUM')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('text-uppercase')
  })

  it('renders low severity with correct styling', () => {
    renderWithTheme(<SeverityBadge severity={SeverityLevel.LOW} />)
    
    const badge = screen.getByText('LOW')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('text-uppercase')
  })

  it('renders unknown severity for null input', () => {
    renderWithTheme(<SeverityBadge severity={null} />)
    
    const badge = screen.getByText('UNKNOWN')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('text-uppercase')
  })

  it('shows icons when showIcon is true', () => {
    renderWithTheme(<SeverityBadge severity={SeverityLevel.CRITICAL} showIcon={true} />)
    
    const badge = screen.getByText(/🔴.*CRITICAL/)
    expect(badge).toBeInTheDocument()
  })

  it('hides icons when showIcon is false', () => {
    renderWithTheme(<SeverityBadge severity={SeverityLevel.CRITICAL} showIcon={false} />)
    
    const badge = screen.getByText('CRITICAL')
    expect(badge).toBeInTheDocument()
    expect(badge.textContent).not.toMatch(/🔴/)
  })

  it('accepts additional className props', () => {
    renderWithTheme(<SeverityBadge severity={SeverityLevel.HIGH} className="custom-class" />)
    
    const badge = screen.getByText('HIGH')
    expect(badge).toHaveClass('custom-class')
    expect(badge).toHaveClass('text-uppercase')
  })

  it('forwards other props to Badge component', () => {
    renderWithTheme(<SeverityBadge severity={SeverityLevel.LOW} data-testid="custom-badge" />)
    
    expect(screen.getByTestId('custom-badge')).toBeInTheDocument()
  })

  it('uses design tokens for styling', () => {
    renderWithTheme(<SeverityBadge severity={SeverityLevel.CRITICAL} />)
    
    const badge = screen.getByText('CRITICAL')
    const styles = window.getComputedStyle(badge)
    
    // The component should apply inline styles from design tokens
    expect(badge.getAttribute('style')).toContain('background-color')
    expect(badge.getAttribute('style')).toContain('color')
    expect(badge.getAttribute('style')).toContain('border-radius')
  })
})