import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ChatWindow from './ChatWindow'

function jsonResponse(body, ok = true) {
  return Promise.resolve({ ok, status: ok ? 200 : 500, json: async () => body })
}

describe('ChatWindow', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
    // history load on mount — no prior messages by default
    fetch.mockImplementation((url) => {
      if (String(url).includes('/history/')) return jsonResponse({ messages: [] })
      return jsonResponse({})
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the welcome message on mount', async () => {
    render(<ChatWindow sessionId="s1" apiUrl="https://api.test" apiKey="key" />)
    expect(await screen.findByText(/I'm AdminIE, your AI assistant/i)).toBeInTheDocument()
  })

  it('loads and renders prior conversation history', async () => {
    fetch.mockImplementation((url) => {
      if (String(url).includes('/history/')) {
        return jsonResponse({
          messages: [
            { role: 'human', content: 'How do I export a report?' },
            { role: 'ai', content: 'Go to Finance > Export.' },
          ],
        })
      }
      return jsonResponse({})
    })
    render(<ChatWindow sessionId="s1" apiUrl="https://api.test" apiKey="key" />)
    expect(await screen.findByText('How do I export a report?')).toBeInTheDocument()
    expect(screen.getByText('Go to Finance > Export.')).toBeInTheDocument()
  })

  it('sends a message and displays the reply', async () => {
    fetch.mockImplementation((url) => {
      if (String(url).includes('/history/')) return jsonResponse({ messages: [] })
      if (String(url).endsWith('/chat')) {
        return jsonResponse({ session_id: 's1', answer: 'Here is how...', escalated: false, tutorial: null })
      }
      return jsonResponse({})
    })
    const user = userEvent.setup()
    render(<ChatWindow sessionId="s1" apiUrl="https://api.test" apiKey="key" />)

    await screen.findByText(/I'm AdminIE/i)
    const textarea = screen.getByPlaceholderText('Ask me anything...')
    await user.type(textarea, 'How do I add a deal?')
    await user.click(screen.getByRole('button', { name: 'Send message' })) // send button (icon only)

    await waitFor(() => expect(screen.getByText('Here is how...')).toBeInTheDocument())
    expect(screen.getByText('How do I add a deal?')).toBeInTheDocument()
  })

  it('shows a friendly error when the chat request fails', async () => {
    fetch.mockImplementation((url) => {
      if (String(url).includes('/history/')) return jsonResponse({ messages: [] })
      if (String(url).endsWith('/chat')) return jsonResponse({}, false)
      return jsonResponse({})
    })
    const user = userEvent.setup()
    render(<ChatWindow sessionId="s1" apiUrl="https://api.test" apiKey="key" />)

    await screen.findByText(/I'm AdminIE/i)
    const textarea = screen.getByPlaceholderText('Ask me anything...')
    await user.type(textarea, 'trigger failure{enter}')

    await waitFor(() => expect(screen.getByText(/having trouble connecting/i)).toBeInTheDocument())
  })

  it('shows an escalation notice when the bot hands off to a human', async () => {
    fetch.mockImplementation((url) => {
      if (String(url).includes('/history/')) return jsonResponse({ messages: [] })
      if (String(url).endsWith('/chat')) {
        return jsonResponse({
          session_id: 's1',
          answer: 'I have flagged this.',
          escalated: true,
          tutorial: null,
        })
      }
      return jsonResponse({})
    })
    const user = userEvent.setup()
    render(<ChatWindow sessionId="s1" apiUrl="https://api.test" apiKey="key" />)

    await screen.findByText(/I'm AdminIE/i)
    await user.type(screen.getByPlaceholderText('Ask me anything...'), 'I am furious{enter}')

    expect(await screen.findByText(/flagged this conversation for our support team/i)).toBeInTheDocument()
  })

  it('opens the ticket form via Get Help and returns via Back', async () => {
    const user = userEvent.setup()
    render(<ChatWindow sessionId="s1" apiUrl="https://api.test" apiKey="key" />)
    await screen.findByText(/I'm AdminIE/i)

    await user.click(screen.getByRole('button', { name: /get help/i }))
    expect(screen.getByText('Submit a support ticket')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(await screen.findByText(/I'm AdminIE/i)).toBeInTheDocument()
  })

  it('lets a user skip the ticket form and escalate to a human directly', async () => {
    fetch.mockImplementation((url) => {
      if (String(url).includes('/history/')) return jsonResponse({ messages: [] })
      if (String(url).endsWith('/escalate')) return jsonResponse({ status: 'ok', detail: 'notified' })
      return jsonResponse({})
    })
    const user = userEvent.setup()
    render(<ChatWindow sessionId="s1" apiUrl="https://api.test" apiKey="key" />)
    await screen.findByText(/I'm AdminIE/i)

    await user.click(screen.getByRole('button', { name: /get help/i }))
    await user.click(screen.getByRole('button', { name: /flag this conversation for a human now/i }))

    expect(await screen.findByText(/flagged this conversation for our support team/i)).toBeInTheDocument()
  })
})
