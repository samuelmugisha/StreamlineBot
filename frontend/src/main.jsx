import React from 'react'
import ReactDOM from 'react-dom/client'
import * as Sentry from '@sentry/react'
import App from './App.jsx'
import './index.css'

// Optional error tracking — only activates when VITE_SENTRY_DSN is set,
// so the widget works without a Sentry account.
if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || 'production',
    tracesSampleRate: 0.1,
    sendDefaultPii: false,
  })
}

const r = document.documentElement
if (import.meta.env.VITE_PRIMARY_COLOR)
  r.style.setProperty('--brand-primary', import.meta.env.VITE_PRIMARY_COLOR)
if (import.meta.env.VITE_PRIMARY_LIGHT)
  r.style.setProperty('--brand-light', import.meta.env.VITE_PRIMARY_LIGHT)
if (import.meta.env.VITE_ACCENT_COLOR)
  r.style.setProperty('--brand-accent', import.meta.env.VITE_ACCENT_COLOR)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
