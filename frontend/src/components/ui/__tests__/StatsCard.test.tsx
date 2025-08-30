/**
 * Unit tests for StatsCard component
 */
import { render, screen } from '@testing-library/react'
import StatsCard from '../StatsCard'
import { ThemeProvider } from '../../../providers/ThemeProvider'
import { Shield } from 'lucide-react'

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider>
      {component}
    </ThemeProvider>
  )
}

describe('StatsCard', () => {
  it('renders basic stats card with title and value', () => {
    renderWithTheme(
      <StatsCard title="Total Dependencies" value={42} />
    )
    
    expect(screen.getByText('Total Dependencies')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renders with string values', () => {
    renderWithTheme(
      <StatsCard title="Scan Type" value="CLI Scan" />
    )
    
    expect(screen.getByText('CLI Scan')).toBeInTheDocument()
  })

  it('renders with icon when provided', () => {
    renderWithTheme(
      <StatsCard 
        title="Security Score" 
        value={95} 
        icon={<Shield data-testid="shield-icon" />} 
      />
    )
    
    expect(screen.getByTestId('shield-icon')).toBeInTheDocument()
  })

  it('renders subtitle when provided', () => {
    renderWithTheme(
      <StatsCard 
        title="Vulnerabilities" 
        value={3} 
        subtitle="Found in scan" 
      />
    )
    
    expect(screen.getByText('Found in scan')).toBeInTheDocument()
  })

  it('renders trend indicator when provided', () => {
    renderWithTheme(
      <StatsCard 
        title="Security Score" 
        value={95} 
        trend={{ value: 5, isPositive: true, label: 'vs last scan' }}
      />
    )
    
    expect(screen.getByText('↑')).toBeInTheDocument()
    expect(screen.getByText(/5% vs last scan/)).toBeInTheDocument()
  })

  it('renders negative trend indicator', () => {
    renderWithTheme(
      <StatsCard 
        title="Security Score" 
        value={85} 
        trend={{ value: 10, isPositive: false, label: 'vs last scan' }}
      />
    )
    
    expect(screen.getByText('↓')).toBeInTheDocument()
    expect(screen.getByText(/10% vs last scan/)).toBeInTheDocument()
  })

  it('applies variant styling correctly', () => {
    renderWithTheme(
      <StatsCard title="Test" value={100} variant="danger" />
    )
    
    const card = document.querySelector('.card')
    const computedStyle = window.getComputedStyle(card)
    expect(computedStyle.getPropertyValue('border-left-width')).toBe('4px')
    expect(computedStyle.getPropertyValue('border-left-color')).toBeTruthy()
  })

  it('accepts custom className', () => {
    renderWithTheme(
      <StatsCard title="Test" value={100} className="custom-stats-card" />
    )
    
    const card = document.querySelector('.card')
    expect(card).toHaveClass('custom-stats-card')
  })

  it('uses design tokens for styling', () => {
    renderWithTheme(
      <StatsCard title="Test" value={100} variant="primary" />
    )
    
    const card = document.querySelector('.card')
    
    // Should use design token values for styling
    expect(card).toHaveAttribute('style')
    const style = card.getAttribute('style')
    expect(style).toContain('border-radius')
    expect(style).toContain('box-shadow')
    expect(style).toContain('background-color')
  })

  it('renders with all props combined', () => {
    renderWithTheme(
      <StatsCard 
        title="Complete Test" 
        value="Success" 
        variant="success"
        subtitle="All tests passing"
        icon={<Shield data-testid="test-icon" />}
        trend={{ value: 15, isPositive: true, label: 'improvement' }}
        className="full-test"
      />
    )
    
    expect(screen.getByText('Complete Test')).toBeInTheDocument()
    expect(screen.getByText('Success')).toBeInTheDocument()
    expect(screen.getByText('All tests passing')).toBeInTheDocument()
    expect(screen.getByTestId('test-icon')).toBeInTheDocument()
    expect(screen.getByText('↑')).toBeInTheDocument()
    expect(screen.getByText(/15% improvement/)).toBeInTheDocument()
    
    const card = document.querySelector('.card')
    expect(card).toHaveClass('full-test')
  })

  it('handles missing optional props gracefully', () => {
    renderWithTheme(
      <StatsCard title="Minimal" value={0} />
    )
    
    expect(screen.getByText('Minimal')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument()
    
    // Should not render optional elements
    expect(screen.queryByText(/↑/)).not.toBeInTheDocument()
    expect(screen.queryByText(/↓/)).not.toBeInTheDocument()
  })
})