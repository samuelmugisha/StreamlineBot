import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

const r = document.documentElement
if (import.meta.env.VITE_PRIMARY_COLOR) r.style.setProperty('--brand-primary', import.meta.env.VITE_PRIMARY_COLOR)
if (import.meta.env.VITE_PRIMARY_LIGHT)  r.style.setProperty('--brand-light',   import.meta.env.VITE_PRIMARY_LIGHT)
if (import.meta.env.VITE_ACCENT_COLOR)   r.style.setProperty('--brand-accent',  import.meta.env.VITE_ACCENT_COLOR)

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
