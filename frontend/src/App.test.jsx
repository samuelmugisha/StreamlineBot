import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() => Promise.resolve({ ok: true, json: async () => ({ messages: [] }) }))
    )
    localStorage.clear()
    delete window.ADMINIE_SESSION_ID
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the closed floating launcher button', () => {
    render(<App />)
    expect(screen.getByRole('button', { name: /chat with adminie/i })).toBeInTheDocument()
  })

  it('opens the chat window when the launcher is clicked', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: /chat with adminie/i }))
    expect(await screen.findByText(/AI Support Assistant/i)).toBeInTheDocument()
  })

  it('persists a generated session id in localStorage across mounts', () => {
    const { unmount } = render(<App />)
    const id = localStorage.getItem('adminiebot_session')
    expect(id).toBeTruthy()
    unmount()
    render(<App />)
    expect(localStorage.getItem('adminiebot_session')).toBe(id)
  })
})
