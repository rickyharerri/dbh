import { useId, useState, type ReactNode } from 'react'

/** Plain-language explanation shown on hover, focus or tap. */
export function InfoTip({ text, label }: { text: string; label: string }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  return (
    <span className="relative inline-flex align-middle">
      <button
        type="button"
        aria-label={`What does “${label}” mean?`}
        aria-expanded={open}
        aria-describedby={open ? id : undefined}
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
        className="flex h-6 w-6 items-center justify-center rounded-full text-sky-800 hover:bg-sky-50"
      >
        <svg viewBox="0 0 20 20" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
          <circle cx="10" cy="10" r="8" />
          <path d="M10 9v5M10 6.2v.1" strokeLinecap="round" />
        </svg>
      </button>
      {open && (
        <span
          role="tooltip"
          id={id}
          className="absolute left-1/2 top-full z-30 mt-1 w-64 max-w-[75vw] -translate-x-1/2 rounded-md border border-slate-200 bg-white p-3 text-sm font-normal leading-snug text-slate-800 shadow-md"
        >
          {text}
        </span>
      )}
    </span>
  )
}

export function ErrorState({ title, message, details, onRetry }: {
  title?: string; message: string; details?: string[]; onRetry?: () => void
}) {
  return (
    <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-900">
      {title && <p className="font-semibold">{title}</p>}
      <p>{message}</p>
      {details && details.length > 0 && (
        <p className="mt-2 text-sm">
          Configuration still needed: <code className="rounded bg-white/70 px-1">{details.join(', ')}</code>
        </p>
      )}
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn btn-secondary mt-3">Try again</button>
      )}
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-slate-700">
      <p className="font-semibold text-slate-900">{title}</p>
      {children && <div className="mt-1">{children}</div>}
    </div>
  )
}

export function Notice({ children, tone = 'info' }: { children: ReactNode; tone?: 'info' | 'warn' }) {
  const cls = tone === 'warn' ? 'border-amber-300 bg-amber-50 text-amber-950' : 'border-sky-200 bg-sky-50 text-sky-950'
  return <div className={`rounded-lg border p-3 text-sm ${cls}`}>{children}</div>
}

export function Disclaimer({ kind = 'historical' }: { kind?: 'historical' | 'quality' }) {
  return kind === 'quality' ? (
    <Notice tone="warn">
      <strong>Historical nearby records do not establish whether water at this property is safe to drink.</strong>{' '}
      Test your own water.
    </Notice>
  ) : (
    <p className="text-sm text-slate-600">Historical records — not a water safety certification.</p>
  )
}

export function PageTitle({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="mb-5">
      <h1 className="text-2xl font-semibold sm:text-3xl">{title}</h1>
      {children && <p className="mt-1 max-w-3xl text-lg text-slate-700">{children}</p>}
    </div>
  )
}
