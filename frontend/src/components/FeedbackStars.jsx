import { useState } from 'react'

const LOW_RATING_THRESHOLD = 3

export default function FeedbackStars({ sessionId, apiUrl, apiKey, question, answer, onEscalated }) {
  const [rating, setRating] = useState(0)
  const [hover, setHover] = useState(0)
  const [comment, setComment] = useState('')
  const [stage, setStage] = useState('rate') // 'rate' | 'comment' | 'sending' | 'done'

  async function submit(value, commentText) {
    setStage('sending')
    try {
      const res = await fetch(`${apiUrl}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Key': apiKey },
        body: JSON.stringify({
          session_id: sessionId,
          question,
          answer,
          rating: value,
          ...(commentText ? { comment: commentText } : {}),
        }),
      })
      if (res.ok) {
        const data = await res.json()
        if (data.escalated) onEscalated?.()
      }
    } catch {
      // best-effort — feedback failures shouldn't disrupt the chat
    } finally {
      setStage('done')
    }
  }

  function handleStarClick(value) {
    setRating(value)
    if (value <= LOW_RATING_THRESHOLD) {
      setStage('comment')
    } else {
      submit(value, '')
    }
  }

  if (stage === 'done') {
    return <p className="text-[10px] text-slate-400 mt-1 ml-1">Thanks for your feedback!</p>
  }

  return (
    <div className="mt-1 ml-1">
      {stage !== 'comment' && (
        <div className="flex items-center gap-0.5">
          <span className="text-[10px] text-slate-400 mr-1">Was this helpful?</span>
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              disabled={stage === 'sending'}
              onMouseEnter={() => setHover(n)}
              onMouseLeave={() => setHover(0)}
              onClick={() => handleStarClick(n)}
              className="text-sm leading-none disabled:opacity-50"
              aria-label={`Rate ${n} star${n > 1 ? 's' : ''}`}
            >
              <span className={(hover || rating) >= n ? 'text-amber-400' : 'text-slate-300'}>★</span>
            </button>
          ))}
        </div>
      )}

      {stage === 'comment' && (
        <div className="max-w-[260px]">
          <p className="text-[10px] text-slate-400 mb-1">
            Sorry about that — what could I have done better? (optional)
          </p>
          <div className="flex gap-1.5">
            <input
              type="text"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Tell us more..."
              className="flex-1 text-xs bg-slate-100 rounded-lg px-2 py-1 focus:outline-none focus:ring-1 focus:ring-brand-primary"
            />
            <button
              type="button"
              onClick={() => submit(rating, comment.trim())}
              className="text-xs font-semibold text-white bg-brand-primary hover:bg-brand-light px-3 py-1 rounded-lg transition-colors shrink-0"
            >
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
