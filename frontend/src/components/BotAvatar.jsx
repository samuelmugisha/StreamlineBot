/* Bot avatar icon — single chat bubble SVG (inline, no external dep) */
export default function BotAvatar({ size = 40, showDot = false }) {
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <div className="w-full h-full rounded-full flex items-center justify-center shadow-md bg-white border border-slate-100">
        <svg viewBox="0 0 64 64" fill="none" style={{ width: size * 0.62, height: size * 0.62 }}>
          {/* Chat bubble */}
          <rect x="12" y="14" width="40" height="26" rx="13" fill="#1B3A6B" />
          <path d="M20 40 L14 50 L30 40 Z" fill="#1B3A6B" />
        </svg>
      </div>
      {showDot && (
        <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-400 border-2 border-white rounded-full" />
      )}
    </div>
  )
}
