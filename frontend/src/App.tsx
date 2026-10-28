import { lazy, Suspense, useEffect, useState } from 'react'
import Header from './components/Header'
import LoadingState from './components/LoadingState'
import Navigation from './components/Navigation'
import WellDetails from './components/WellDetails'
import { useActions, useAppState, useHealth } from './state/AppContext'
import type { TabId } from './types/groundwater'

// Each page is its own chunk: the first screen only downloads what it needs.
const ExplorePage = lazy(() => import('./pages/ExplorePage'))
const WaterQualityPage = lazy(() => import('./pages/WaterQualityPage'))
const ComparePage = lazy(() => import('./pages/ComparePage'))
const GeniePage = lazy(() => import('./pages/GeniePage'))

const PAGES: Record<TabId, React.LazyExoticComponent<(p: { active: boolean }) => JSX.Element>> = {
  explore: ExplorePage, quality: WaterQualityPage, compare: ComparePage, ask: GeniePage,
}

function ModeBanner() {
  const health = useHealth()
  if (health?.mode !== 'demo') return null
  return (
    <div role="note" className="border-b border-amber-400 bg-amber-100 px-4 py-2 text-center text-amber-950">
      <strong>Demo mode.</strong> Every well, measurement and quality result shown here is synthetic and randomly generated for
      testing the interface. It is not Alberta Water Well Information Database data.
    </div>
  )
}

export default function App() {
  const { tab, detailsWellId } = useAppState()
  const { openDetails } = useActions()
  // Pages stay mounted once opened (just hidden), so switching tabs is instant and keeps map position and scroll.
  const [visited, setVisited] = useState<Set<TabId>>(() => new Set([tab]))
  useEffect(() => setVisited((v) => (v.has(tab) ? v : new Set(v).add(tab))), [tab])

  return (
    <>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[2000] focus:rounded focus:bg-white focus:p-2">Skip to content</a>
      <ModeBanner />
      <Header />
      <Navigation />
      <main id="main" className="mx-auto max-w-6xl px-4 py-6">
        {(Object.keys(PAGES) as TabId[]).map((id) => {
          if (!visited.has(id)) return null
          const Page = PAGES[id]
          return (
            <div key={id} role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`} hidden={tab !== id}>
              <Suspense fallback={<LoadingState label="Loading…" />}>
                <Page active={tab === id} />
              </Suspense>
            </div>
          )
        })}
      </main>
      <WellDetails wellId={detailsWellId} onClose={() => openDetails(null)} />
      <footer className="border-t border-slate-200 bg-slate-50 px-4 py-5 text-center text-sm text-slate-700">
        Historical records — not a water safety certification. Test your own water.
      </footer>
    </>
  )
}
