import BotAvatar from './BotAvatar'

export default function TypingIndicator() {
  return (
    <div className="flex items-end gap-2 mb-3">
      <BotAvatar size={28} />
      <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
        <div className="flex gap-1 items-center h-4">
          {[0, 150, 300].map((delay, i) => (
            <span
              key={i}
              className="w-2 h-2 bg-brand-primary rounded-full animate-bounce"
              style={{ animationDelay: `${delay}ms`, opacity: 0.5 }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
