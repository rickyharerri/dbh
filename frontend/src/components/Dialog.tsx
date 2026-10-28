import { useEffect, useRef, type ReactNode } from 'react'

const FOCUSABLE = 'a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])'

/** Accessible modal: Escape closes, focus is trapped inside and restored afterwards. */
export default function Dialog({ open, onClose, title, children, side = false }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode; side?: boolean
}) {
  const panel = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const previous = document.activeElement as HTMLElement | null
    panel.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.stopPropagation(); onClose(); return }
      if (e.key !== 'Tab' || !panel.current) return
      const items = Array.from(panel.current.querySelectorAll<HTMLElement>(FOCUSABLE))
      if (items.length === 0) return
      const first = items[0], last = items[items.length - 1]
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('keydown', onKey); previous?.focus?.() }
  }, [open, onClose])

  if (!open) return null
  return (
    <div className={`fixed inset-0 z-[1000] flex bg-slate-900/40 ${side ? 'justify-end' : 'items-center justify-center p-4'}`}
         onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={`overflow-y-auto bg-white p-5 outline-none ${side ? 'h-full w-full max-w-md' : 'max-h-full w-full max-w-xl rounded-lg'}`}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <h2 className="text-xl font-semibold">{title}</h2>
          <button type="button" onClick={onClose} className="btn btn-secondary !min-h-[40px] !px-3">Close</button>
        </div>
        {children}
      </div>
    </div>
  )
}
