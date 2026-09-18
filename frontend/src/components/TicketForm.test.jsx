import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TicketForm from './TicketForm'

describe('TicketForm', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('submits the ticket and shows a confirmation', async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ok', ticket_id: 'abc-123' }) })
    const user = userEvent.setup()

    render(<TicketForm apiUrl="https://api.test" apiKey="key" sessionId="session-1" onBack={() => {}} />)

    await user.type(screen.getByPlaceholderText('Your name'), 'Jane Doe')
    await user.type(screen.getByPlaceholderText('you@example.com'), 'jane@example.com')
    await user.selectOptions(screen.getByDisplayValue('Select...'), 'General')
    await user.type(screen.getByPlaceholderText('One-line summary of your issue'), 'Cannot export report')
    await user.type(
      screen.getByPlaceholderText('Describe your issue in detail...'),
      'The button is greyed out.'
    )

    await user.click(screen.getByRole('button', { name: /submit ticket/i }))

    await waitFor(() => expect(screen.getByText('Ticket submitted!')).toBeInTheDocument())

    expect(fetch).toHaveBeenCalledWith(
      'https://api.test/ticket',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'X-API-Key': 'key' }),
      })
    )
    const body = JSON.parse(fetch.mock.calls[0][1].body)
    expect(body).toMatchObject({ name: 'Jane Doe', email: 'jane@example.com', session_id: 'session-1' })
  })

  it('shows an error message when the request fails', async () => {
    fetch.mockResolvedValueOnce({ ok: false, status: 500 })
    const user = userEvent.setup()

    render(<TicketForm apiUrl="https://api.test" apiKey="key" sessionId="session-1" onBack={() => {}} />)

    await user.type(screen.getByPlaceholderText('Your name'), 'Jane Doe')
    await user.type(screen.getByPlaceholderText('you@example.com'), 'jane@example.com')
    await user.selectOptions(screen.getByDisplayValue('Select...'), 'General')
    await user.type(screen.getByPlaceholderText('One-line summary of your issue'), 'x')
    await user.type(screen.getByPlaceholderText('Describe your issue in detail...'), 'x')

    await user.click(screen.getByRole('button', { name: /submit ticket/i }))

    await waitFor(() => expect(screen.getByText(/could not submit ticket/i)).toBeInTheDocument())
  })

  it('calls onBack when Back is clicked', async () => {
    const onBack = vi.fn()
    const user = userEvent.setup()
    render(<TicketForm apiUrl="https://api.test" apiKey="key" sessionId="session-1" onBack={onBack} />)
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(onBack).toHaveBeenCalledTimes(1)
  })
})
