import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import FeedbackStars from './FeedbackStars'

describe('FeedbackStars', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('submits a high rating immediately without asking for a comment', async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ok', escalated: false }) })
    const user = userEvent.setup()

    render(<FeedbackStars apiUrl="https://api.test" apiKey="key" sessionId="s1" question="q" answer="a" />)
    await user.click(screen.getByRole('button', { name: 'Rate 5 stars' }))

    await waitFor(() => expect(screen.getByText('Thanks for your feedback!')).toBeInTheDocument())
    const body = JSON.parse(fetch.mock.calls[0][1].body)
    expect(body.rating).toBe(5)
    expect(body.comment).toBeUndefined()
  })

  it('asks for an optional comment on a low rating, then submits it', async () => {
    fetch.mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ok', escalated: true }) })
    const onEscalated = vi.fn()
    const user = userEvent.setup()

    render(
      <FeedbackStars
        apiUrl="https://api.test"
        apiKey="key"
        sessionId="s1"
        question="q"
        answer="a"
        onEscalated={onEscalated}
      />
    )
    await user.click(screen.getByRole('button', { name: 'Rate 2 stars' }))
    expect(screen.getByPlaceholderText('Tell us more...')).toBeInTheDocument()

    await user.type(screen.getByPlaceholderText('Tell us more...'), 'The button was hard to find')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => expect(onEscalated).toHaveBeenCalledTimes(1))
    const body = JSON.parse(fetch.mock.calls[0][1].body)
    expect(body).toMatchObject({ rating: 2, comment: 'The button was hard to find' })
  })

  it('does not crash the widget when the feedback request fails', async () => {
    fetch.mockRejectedValueOnce(new Error('network down'))
    const user = userEvent.setup()

    render(<FeedbackStars apiUrl="https://api.test" apiKey="key" sessionId="s1" question="q" answer="a" />)
    await user.click(screen.getByRole('button', { name: 'Rate 5 stars' }))

    await waitFor(() => expect(screen.getByText('Thanks for your feedback!')).toBeInTheDocument())
  })
})
