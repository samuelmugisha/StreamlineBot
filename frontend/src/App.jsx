import { useState, useEffect } from 'react'
import { v4 as uuidv4 } from 'uuid'
import ChatWindow from './components/ChatWindow'
import BotAvatar from './components/BotAvatar'
import ErrorBoundary from './components/ErrorBoundary'

const COMPANY_NAME = import.meta.env.VITE_COMPANY_NAME || 'AdminIE'

// Runtime config — the grants system MUST set window.ADMINIE_* in a <script> tag
// that appears BEFORE the widget bundle is loaded, otherwise these values
// will not be present when getConfig() runs at component mount time.
// Falls back to build-time env vars for standalone / dev use.
const getConfig = () => ({
  sessionId: window.ADMINIE_SESSION_ID || getStoredSessionId(),
  apiUrl: window.ADMINIE_API_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000',
  apiKey: window.ADMINIE_API_KEY || import.meta.env.VITE_API_KEY || '',
})

function getStoredSessionId() {
  let id = localStorage.getItem('adminiebot_session')
  if (!id) {
    id = uuidv4()
    localStorage.setItem('adminiebot_session', id)
  }
  return id
}

function resetSession() {
  const id = uuidv4()
  localStorage.setItem('adminiebot_session', id)
  return id
}

export default function App() {
  const [config] = useState(getConfig)
  const [sessionId, setSessionId] = useState(config.sessionId)
  const [open, setOpen] = useState(false)
  const [showPreview, setShowPreview] = useState(false)

  useEffect(() => {
    if (localStorage.getItem('adminiebot_preview_dismissed')) return
    const t = setTimeout(() => setShowPreview(true), 2000)
    return () => clearTimeout(t)
  }, [])

  function toggleChat() {
    setOpen((prev) => !prev)
    setShowPreview(false)
  }

  function handleNewChat() {
    // Only reset localStorage-based sessions — never override grants-system user IDs
    if (!window.ADMINIE_SESSION_ID) {
      setSessionId(resetSession())
    }
  }

  return (
    <>
      {/* ⚠️  DEV ONLY — remove before embedding in grants system ⚠️  */}
      {import.meta.env.DEV && (
        <div className="min-h-screen bg-slate-100 flex items-center justify-center">
          <div className="text-center text-slate-400">
            <p className="text-lg font-medium">AdminIE Grant Management System</p>
            <p className="text-sm mt-1">Development preview</p>
          </div>
        </div>
      )}

      {/* Widget — fixed bottom-right */}
      <div className="fixed bottom-6 right-6 flex flex-col items-end gap-3 z-50">
        {/* Chat window wrapped in its own ErrorBoundary */}
        {open && (
          <div style={{ animation: 'fadeInUp 0.22s ease-out' }}>
            <ErrorBoundary>
              <ChatWindow
                sessionId={sessionId}
                apiUrl={config.apiUrl}
                apiKey={config.apiKey}
                onClose={() => setOpen(false)}
                onNewChat={handleNewChat}
              />
            </ErrorBoundary>
          </div>
        )}

        {/* Preview bubble */}
        {!open && showPreview && (
          <div
            style={{ animation: 'fadeInUp 0.22s ease-out' }}
            className="flex items-start gap-3 bg-white rounded-2xl shadow-xl border border-slate-100 p-3 max-w-[260px]"
          >
            <BotAvatar size={40} showDot />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-xs font-bold text-slate-800 leading-tight">{COMPANY_NAME}</p>
                  <p className="text-[10px] text-slate-400">AI Support Assistant</p>
                </div>
                <button
                  onClick={() => {
                    setShowPreview(false)
                    localStorage.setItem('adminiebot_preview_dismissed', '1')
                  }}
                  className="text-slate-300 hover:text-slate-500 shrink-0"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
              <p className="text-xs text-slate-600 mt-1 leading-snug">
                👋 Hi! I'm {COMPANY_NAME}. Ask me anything about {COMPANY_NAME} modules.
              </p>
              <button
                onClick={toggleChat}
                className="mt-2 text-[11px] font-semibold text-white bg-brand-primary hover:bg-brand-light px-3 py-1 rounded-full transition-colors"
              >
                Chat now
              </button>
            </div>
          </div>
        )}

        {/* Floating avatar button */}
        <button
          onClick={toggleChat}
          aria-label="Chat with AdminIE"
          className="relative focus:outline-none hover:scale-105 transition-transform duration-200"
        >
          {open ? (
            <div className="w-14 h-14 rounded-full bg-brand-primary shadow-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
          ) : (
            <BotAvatar size={56} showDot />
          )}
        </button>
      </div>

      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(12px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0)    scale(1); }
        }
      `}</style>
    </>
  )
}
