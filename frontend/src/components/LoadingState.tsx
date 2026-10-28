export function Spinner({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

/** Announced to screen readers; skeleton blocks keep the layout from jumping while data loads. */
export default function LoadingState({ label = 'Loading…', blocks = 0 }: { label?: string; blocks?: number }) {
  return (
    <div role="status" aria-live="polite" className="text-slate-700">
      <p className="flex items-center gap-2 text-base">
        <Spinner className="h-5 w-5 text-teal-700" />
        <span>{label}</span>
      </p>
      {blocks > 0 && (
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-hidden="true">
          {Array.from({ length: blocks }, (_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-lg bg-slate-100" />
          ))}
        </div>
      )}
    </div>
  )
}
