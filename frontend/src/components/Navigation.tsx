import { useRef, useState } from 'react'
import { useActions, useAppState } from '../state/AppContext'
import type { TabId } from '../types/groundwater'

export const TABS: { id: TabId; label: string }[] = [
  { id: 'explore', label: 'Explore Property' },
  { id: 'quality', label: 'Water Quality' },
  { id: 'compare', label: 'Compare Properties' },
  { id: 'ask', label: 'Ask AquaWise' },
]

export default function Navigation() {
  const { tab } = useAppState()
  const { setTab } = useActions()
  const [menu, setMenu] = useState(false)
  const refs = useRef<Record<string, HTMLButtonElement | null>>({})
  const current = TABS.find((t) => t.id === tab)!

  const onKeyDown = (e: React.KeyboardEvent, index: number) => {
    const step = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0
    if (!step) return
    e.preventDefault()
    const next = TABS[(index + step + TABS.length) % TABS.length]
    setTab(next.id)
    refs.current[next.id]?.focus()
  }

  return (
    <nav aria-label="Main" className="border-b border-slate-200 bg-white">
      <div className="mx-auto max-w-6xl px-4">
        {/* compact menu on small screens */}
        <div className="py-2 md:hidden">
          <button
            type="button" className="btn btn-secondary w-full justify-between" aria-expanded={menu} aria-controls="mobile-menu"
            onClick={() => setMenu((v) => !v)}
          >
            <span>{current.label}</span>
            <span aria-hidden="true">{menu ? '▲' : '▼'}</span>
          </button>
          {menu && (
            <ul id="mobile-menu" className="mt-2 overflow-hidden rounded-md border border-slate-200">
              {TABS.map((t) => (
                <li key={t.id}>
                  <button
                    type="button"
                    aria-current={t.id === tab ? 'page' : undefined}
                    onClick={() => { setTab(t.id); setMenu(false) }}
                    className={`block min-h-[44px] w-full px-4 py-2 text-left text-base ${t.id === tab ? 'bg-teal-50 font-semibold text-teal-900' : 'hover:bg-slate-50'}`}
                  >
                    {t.label}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* horizontal tabs on desktop */}
        <div role="tablist" aria-label="Sections" className="hidden gap-1 md:flex">
          {TABS.map((t, i) => {
            const active = t.id === tab
            return (
              <button
                key={t.id}
                ref={(el) => { refs.current[t.id] = el }}
                role="tab"
                id={`tab-${t.id}`}
                aria-selected={active}
                aria-controls={`panel-${t.id}`}
                tabIndex={active ? 0 : -1}
                onClick={() => setTab(t.id)}
                onKeyDown={(e) => onKeyDown(e, i)}
                className={`-mb-px min-h-[48px] border-b-4 px-4 text-base font-semibold transition-colors ${
                  active ? 'border-teal-700 text-teal-900' : 'border-transparent text-slate-700 hover:border-slate-300 hover:text-slate-900'
                }`}
              >
                {t.label}
              </button>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
