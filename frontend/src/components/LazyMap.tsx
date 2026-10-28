import { lazy, Suspense } from 'react'
import type { WellMapProps } from './WellMap'

// Leaflet is ~150 kB: load it only when a map is first shown so the page text appears immediately.
const WellMap = lazy(() => import('./WellMap'))

export default function LazyMap(props: WellMapProps) {
  return (
    <Suspense
      fallback={
        <div role="status" className="flex h-[340px] items-center justify-center rounded-lg border border-slate-300 bg-slate-50 text-slate-700 sm:h-[460px]">
          Loading map…
        </div>
      }
    >
      <WellMap {...props} />
    </Suspense>
  )
}
