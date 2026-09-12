import { useState, useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import TypingIndicator from './TypingIndicator'
import BotAvatar from './BotAvatar'
import TicketForm from './TicketForm'

const COMPANY_NAME   = import.meta.env.VITE_COMPANY_NAME   || 'AdminIE'
const SUPPORT_EMAIL  = import.meta.env.VITE_SUPPORT_EMAIL  || 'success@adminie.com'
const MODULES_LIST   = import.meta.env.VITE_MODULES_LIST   || 'CRM, Finance, HR, Banking, Programs, Projects, and Policies'

const WELCOME = {
  id: 'welcome',
  role: 'bot',
  content: `Hi there! I'm ${COMPANY_NAME}, your AI assistant. I can help you with ${MODULES_LIST}.\n\nIf I'm unable to help, you can reach the team at ${SUPPORT_EMAIL}.`,
}

const ESCALATION_NOTICE = "I've flagged this conversation for our support team — someone will follow up with you by email shortly."

export default function ChatWindow({ sessionId, apiUrl, apiKey, onClose, onNewChat }) {
  const [messages, setMessages] = useState([WELCOME])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [escalating, setEscalating] = useState(false)
  const [showTicketForm, setShowTicketForm] = useState(false)
  const bottomRef = useRef(null)

  // Silently load prior history on mount; abort if component unmounts before it resolves
  useEffect(() => {
    const controller = new AbortController()

    async function loadHistory() {
      try {
        const res = await fetch(`${apiUrl}/history/${sessionId}`, {
          headers: { 'X-API-Key': apiKey },
          signal: controller.signal,
        })
        if (!res.ok) return
        const data = await res.json()
        if (data.messages?.length > 0) {
          const prior = data.messages.map((m, i) => ({
            id: `history-${i}`,
            role: m.role === 'human' ? 'user' : 'bot',
            content: m.content,
          }))
          setMessages([WELCOME, ...prior])
        }
      } catch (err) {
        if (err.name === 'AbortError') return
        // other errors: silently ignore — welcome message stays
      }
    }

    loadHistory()
    return () => controller.abort()
  }, [sessionId, apiUrl, apiKey])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  function appendEscalationNotice() {
    setMessages(prev => [...prev, {
      id: crypto.randomUUID(),
      role: 'bot',
      content: ESCALATION_NOTICE,
    }])
  }

  async function sendMessage() {
    const text = input.trim()
    if (!text || loading) return

    setMessages(prev => [...prev, {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    }])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${apiUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      const data = await res.json()
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'bot',
        content: data.answer,
        question: text,
        feedbackEnabled: true,
        tutorial: data.tutorial,
      }])
      if (data.escalated) {
        appendEscalationNotice()
      }
    } catch {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'bot',
        content: "Sorry, I'm having trouble connecting right now. Please try again.",
      }])
    } finally {
      setLoading(false)
    }
  }

  async function handleEscalate() {
    if (escalating) return
    setEscalating(true)

    try {
      const res = await fetch(`${apiUrl}/escalate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ session_id: sessionId }),
      })
      if (!res.ok) throw new Error(`Server error: ${res.status}`)
      appendEscalationNotice()
    } catch {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'bot',
        content: "Sorry, I couldn't reach our support team right now. Please email success@adminie.com directly.",
      }])
    } finally {
      setEscalating(false)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  function handleNewChat() {
    setMessages([WELCOME])
    setInput('')
    onNewChat?.()
  }

  return (
    <div className="flex flex-col w-[calc(100vw-3rem)] h-[calc(100svh-6rem)] sm:w-[440px] sm:h-[500px] bg-slate-50 rounded-2xl shadow-2xl overflow-hidden border border-slate-200">

      {/* Header */}
      <div className="bg-brand-primary px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <BotAvatar size={42} showDot />
          <div>
            <p className="text-white font-bold text-sm leading-tight">{COMPANY_NAME}</p>
            <p className="text-white/60 text-[11px]">AI Support Assistant · {COMPANY_NAME}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowTicketForm(true)}
            className="flex flex-col items-center gap-0.5 text-white/60 hover:text-white transition-colors px-1.5 py-1 rounded-lg hover:bg-white/10">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z"/>
            </svg>
            <span className="text-[9px] font-medium leading-none whitespace-nowrap">Get Help</span>
          </button>
          <button
            onClick={handleNewChat}
            title="Start new conversation"
            className="text-white/60 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/10">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
            </svg>
          </button>
          <button onClick={onClose}
            className="text-white/60 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/10">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Messages or Ticket Form */}
      {showTicketForm ? (
        <TicketForm
          apiUrl={apiUrl}
          apiKey={apiKey}
          sessionId={sessionId}
          onBack={() => setShowTicketForm(false)}
        />
      ) : (
        <div className="flex-1 overflow-y-auto chat-scroll px-4 py-4 space-y-1">
          {messages.map(msg => (
            <MessageBubble
              key={msg.id}
              message={msg}
              sessionId={sessionId}
              apiUrl={apiUrl}
              apiKey={apiKey}
              onEscalated={appendEscalationNotice}
            />
          ))}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Input — hidden when ticket form is open */}
      {!showTicketForm && <div className="px-3 pb-3 pt-2 bg-white border-t border-slate-100 shrink-0">
        <div className="flex items-end gap-2 bg-slate-100 rounded-xl px-3 py-2">
          <textarea
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask me anything..."
            className="flex-1 bg-transparent text-sm text-slate-800 placeholder-slate-400 resize-none focus:outline-none max-h-24"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="shrink-0 w-8 h-8 rounded-lg bg-brand-primary disabled:bg-slate-300 flex items-center justify-center transition-colors hover:bg-brand-light">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
            </svg>
          </button>
        </div>
        <p className="text-center text-[10px] text-slate-400 mt-1.5 leading-snug">
          Disclaimer: This chat is facilitated by AI and may produce inaccurate information
        </p>
      </div>}
    </div>
  )
}
