import ReactMarkdown from 'react-markdown'
import BotAvatar from './BotAvatar'
import FeedbackStars from './FeedbackStars'

const markdownComponents = {
  p:      ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em:     ({ children }) => <em className="italic">{children}</em>,
  ul:     ({ children }) => <ul className="list-disc pl-4 my-1 space-y-0.5">{children}</ul>,
  ol:     ({ children }) => <ol className="list-decimal pl-4 my-1 space-y-0.5">{children}</ol>,
  li:     ({ children }) => <li>{children}</li>,
  a:      ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="underline">
      {children}
    </a>
  ),
}

export default function MessageBubble({ message, sessionId, apiUrl, apiKey, onEscalated }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex items-end gap-2 mb-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>

      {/* Avatar */}
      {isUser ? (
        <div className="w-7 h-7 rounded-full bg-brand-accent flex items-center justify-center text-white text-[10px] font-bold shrink-0">
          You
        </div>
      ) : (
        <BotAvatar size={28} />
      )}

      <div className={`max-w-[78%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        {!isUser && (
          <p className="text-[10px] text-slate-400 mb-0.5 ml-1">{import.meta.env.VITE_COMPANY_NAME || 'AdminIE'}</p>
        )}

        <div className={`px-4 py-2.5 text-sm leading-relaxed shadow-sm
          ${isUser
            ? 'bg-brand-primary text-white rounded-2xl rounded-br-none'
            : 'bg-white border border-slate-200 text-slate-800 rounded-2xl rounded-bl-none'
          }`}>
          {isUser ? (
            /* User messages: plain text, preserve line breaks */
            message.content.split('\n').map((line, i, arr) => (
              <span key={i}>{line}{i < arr.length - 1 && <br />}</span>
            ))
          ) : (
            /* Bot messages: render markdown */
            <ReactMarkdown components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          )}

          {!isUser && message.tutorial && (
            <a
              href={message.tutorial.image_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-brand-primary hover:underline"
            >
              📷 View tutorial
            </a>
          )}
        </div>

        {!isUser && message.feedbackEnabled && (
          <FeedbackStars
            sessionId={sessionId}
            apiUrl={apiUrl}
            apiKey={apiKey}
            question={message.question}
            answer={message.content}
            onEscalated={onEscalated}
          />
        )}
      </div>
    </div>
  )
}
