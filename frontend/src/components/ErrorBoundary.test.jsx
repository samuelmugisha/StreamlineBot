import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import ErrorBoundary from './ErrorBoundary'

function Bomb() {
  throw new Error('boom')
}

describe('ErrorBoundary', () => {
  it('renders children when nothing throws', () => {
    render(
      <ErrorBoundary>
        <p>safe content</p>
      </ErrorBoundary>
    )
    expect(screen.getByText('safe content')).toBeInTheDocument()
  })

  it('renders a fallback instead of crashing the whole widget', () => {
    // React logs the caught error to console.error — expected, not a test failure.
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    )
    expect(screen.getByText(/ran into a problem/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
    spy.mockRestore()
  })

  it('lets the user retry after a crash', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>
    )
    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    // Retrying re-mounts the same crashing child, so the fallback reappears —
    // this asserts the retry path doesn't itself throw.
    expect(screen.getByText(/ran into a problem/i)).toBeInTheDocument()
    spy.mockRestore()
  })
})
