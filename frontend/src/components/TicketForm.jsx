import { useState } from 'react'

const MODULES = (import.meta.env.VITE_MODULES_LIST || 'General')
  .split(',')
  .map((m) => m.trim())
  .filter(Boolean)

const PRIORITIES = ['Low', 'Medium', 'Urgent']

const inputCls =
  'mt-0.5 w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-primary/30 bg-white'
const labelCls = 'text-[11px] font-medium text-slate-500 uppercase tracking-wide'

export default function TicketForm({ apiUrl, apiKey, sessionId, onBack, onEscalate, escalating }) {
  const [form, setForm] = useState({
    name: '',
    email: '',
    module: '',
    subject: '',
    description: '',
    priority: 'Medium',
  })
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  function update(field, val) {
    setForm((prev) => ({ ...prev, [field]: val }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const res = await fetch(`${apiUrl}/ticket`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({ ...form, session_id: sessionId }),
      })
      if (!res.ok) throw new Error(`${res.status}`)
      setSubmitted(true)
    } catch {
      setError('Could not submit ticket. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center px-6 text-center gap-4">
        <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
          <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p className="font-semibold text-slate-800">Ticket submitted!</p>
        <p className="text-sm text-slate-500">
          We'll get back to you at <span className="font-medium">{form.email}</span>.
        </p>
        <button onClick={onBack} className="text-sm text-brand-primary hover:underline mt-2">
          Back to chat
        </button>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto chat-scroll px-4 py-4 space-y-3">
      <p className="text-sm font-semibold text-slate-700">Submit a support ticket</p>

      {onEscalate && (
        <button
          type="button"
          onClick={onEscalate}
          disabled={escalating}
          className="text-xs text-brand-primary hover:underline disabled:opacity-50"
        >
          {escalating
            ? 'Notifying support…'
            : 'Prefer to skip the form? Flag this conversation for a human now →'}
        </button>
      )}

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className={labelCls}>Name *</label>
          <input
            required
            value={form.name}
            onChange={(e) => update('name', e.target.value)}
            className={inputCls}
            placeholder="Your name"
          />
        </div>
        <div>
          <label className={labelCls}>Email *</label>
          <input
            required
            type="email"
            value={form.email}
            onChange={(e) => update('email', e.target.value)}
            className={inputCls}
            placeholder="you@example.com"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className={labelCls}>Module *</label>
          <select
            required
            value={form.module}
            onChange={(e) => update('module', e.target.value)}
            className={inputCls}
          >
            <option value="">Select...</option>
            {MODULES.map((m) => (
              <option key={m}>{m}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelCls}>Priority</label>
          <select
            value={form.priority}
            onChange={(e) => update('priority', e.target.value)}
            className={inputCls}
          >
            {PRIORITIES.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className={labelCls}>Subject *</label>
        <input
          required
          value={form.subject}
          onChange={(e) => update('subject', e.target.value)}
          className={inputCls}
          placeholder="One-line summary of your issue"
        />
      </div>

      <div>
        <label className={labelCls}>Description *</label>
        <textarea
          required
          rows={4}
          value={form.description}
          onChange={(e) => update('description', e.target.value)}
          className={`${inputCls} resize-none`}
          placeholder="Describe your issue in detail..."
        />
      </div>

      {error && <p className="text-xs text-red-500">{error}</p>}

      <div className="flex gap-2 pt-1 pb-2">
        <button
          type="button"
          onClick={onBack}
          className="flex-1 text-sm py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
        >
          Back
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="flex-1 text-sm py-2 rounded-lg bg-brand-primary text-white disabled:opacity-50 hover:bg-brand-light transition-colors"
        >
          {submitting ? 'Submitting…' : 'Submit Ticket'}
        </button>
      </div>
    </form>
  )
}
