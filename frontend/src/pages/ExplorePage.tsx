import { lazy, Suspense } from 'react'
import { fmtMeasure, fmtNumber, plural } from '../lib/format'
import { useActions, useAppState, useHealth } from '../state/AppContext'
import DataCoverage from '../components/DataCoverage'
import LazyMap from '../components/LazyMap'
import LoadingState from '../components/LoadingState'
import LocationSearch from '../components/LocationSearch'
import SummaryCard from '../components/SummaryCard'
import WellsTable from '../components/WellsTable'
import { Disclaimer, EmptyState, ErrorState, PageTitle } from '../components/ui'

// Recharts is large: it downloads only once there are results to chart (and is prefetched when Analyze starts).
const HistogramChart = lazy(() => import('../components/HistogramChart'))
const chartFallback = <div role="status" className="h-72 animate-pulse rounded-lg bg-slate-100" aria-label="Loading chart" />

export default function ExplorePage({ active }: { active: boolean }) {
  const s = useAppState()
  const a = useActions()
  const health = useHealth()
  const { location, radiusKm, analysis } = s

  const result = analysis.status === 'success' ? analysis.data : null
  const nearby = result?.nearby
  const sum = result?.summary
  const units = nearby?.units ?? health?.units

  return (
    <div className="space-y-5">
      <PageTitle title="Explore groundwater near your property">
        Select a location in Alberta to explore historical water-well information.
      </PageTitle>

      {health?.mode === 'unconfigured' && (
        <ErrorState
          title="Groundwater data isn’t connected yet"
          message="This copy of AquaWise can’t reach the well records. An administrator needs to finish the Databricks setup."
          details={health.missing_configuration}
        />
      )}
      {health?.warnings.map((w) => <p key={w} className="text-sm text-amber-900" role="status">{w}</p>)}

      <LocationSearch />

      <div>
        <LazyMap
          points={location ? [{ key: 'selected', label: 'Selected location', location, color: '#0f766e' }] : []}
          radiusKm={radiusKm}
          wells={nearby?.wells}
          units={units ?? undefined}
          selectedWellId={s.selectedWellId}
          selectNonce={s.selectNonce}
          onPick={(p) => a.setLocation(p)}
          onSelectWell={a.selectWell}
          onViewDetails={a.openDetails}
          focusNonce={s.focusNonce}
          active={active}
        />
        <p className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-slate-700">
          <span className="inline-flex items-center gap-1.5"><span className="inline-block h-3 w-3 rounded-full border-2 border-white bg-teal-700 ring-1 ring-slate-400" aria-hidden="true" />Selected location</span>
          <span className="inline-flex items-center gap-1.5"><span className="inline-block h-3 w-3 rounded-full bg-sky-500 ring-1 ring-sky-800" aria-hidden="true" />Historical well</span>
          <span>Map markers can’t be reached by keyboard — use the table below the results.</span>
        </p>
      </div>

      {analysis.status === 'loading' && <LoadingState label="Searching nearby wells…" blocks={4} />}
      {analysis.status === 'error' && (
        <ErrorState message={analysis.message} details={analysis.missing} onRetry={analysis.code === 'not_configured' ? undefined : () => void a.analyze()} />
      )}
      {analysis.status === 'idle' && (
        <EmptyState title="No results yet">Choose a location on the map, then select “Analyze Groundwater”.</EmptyState>
      )}

      {nearby && sum && (
        nearby.total_wells === 0 ? (
          <EmptyState title="No nearby wells">
            No historical wells were found within the selected radius. Try increasing the search area.
          </EmptyState>
        ) : (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold">
              Within {nearby.radius_km} km: {plural(nearby.total_wells, 'historical well')}
            </h2>
            {nearby.truncated && (
              <p className="text-slate-700">
                The map and table show the nearest {fmtNumber(nearby.returned_wells, 0)} wells. The figures below use all {fmtNumber(nearby.total_wells, 0)}.
              </p>
            )}

            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <SummaryCard
                title="Nearby wells"
                tip="Historical well records located inside your search circle. Records can be decades old, and a well may no longer exist or be in use."
                value={fmtNumber(sum.total_wells, 0)}
                description={`historical wells within ${sum.radius_km} km`}
                basis="Every record counted once"
              />
              <SummaryCard
                title="Typical well depth"
                tip="How deep nearby wells were drilled. “Typical” is the median: half of the wells are deeper, half are shallower. Wells with no recorded depth are left out, not counted as zero."
                value={sum.depth.available && sum.depth.median !== null ? fmtMeasure(sum.depth.median, sum.depth.unit) : null}
                description="Typical recorded depth below ground"
                basis={`Median of ${fmtNumber(sum.depth.sample_count, 0)} of ${fmtNumber(sum.total_wells, 0)} wells with a recorded depth`}
                unavailableReason={sum.depth.available ? 'No depth was recorded for wells in this area.' : 'Depth is not part of this dataset.'}
              />
              <SummaryCard
                title="Typical well yield"
                tip="How much water a driller reported a well could produce when it was tested. It is a one-time historical figure for that well, not a promise for your property. Wells with no recorded yield are left out."
                value={sum.well_yield.available && sum.well_yield.median !== null ? fmtMeasure(sum.well_yield.median, sum.well_yield.unit) : null}
                description="Typical reported yield"
                basis={`Median of ${fmtNumber(sum.well_yield.sample_count, 0)} of ${fmtNumber(sum.total_wells, 0)} wells with a recorded yield`}
                unavailableReason={sum.well_yield.available ? 'No yield was recorded for wells in this area.' : 'Yield is not part of this dataset.'}
              />
              <SummaryCard
                title="Water quality records"
                tip="How many nearby wells have at least one recorded water-quality test result. This says what data exists, not whether the water is safe."
                value={sum.quality.available ? fmtNumber(sum.quality.wells_with_quality, 0) : null}
                description="wells with water-quality observations"
                basis={`${fmtNumber(sum.quality.observation_count, 0)} observations in total`}
                unavailableReason="Water-quality records are not part of this dataset."
              />
            </div>

            <DataCoverage s={sum} />

            <Suspense fallback={<div className="grid gap-4 lg:grid-cols-2">{chartFallback}{chartFallback}</div>}>
              <div className="grid gap-4 lg:grid-cols-2">
                <HistogramChart title="Well depth" noun="depth" histogram={sum.histograms.depth} available={sum.depth.available} color="#0f766e" />
                <HistogramChart title="Well yield" noun="yield" histogram={sum.histograms.well_yield} available={sum.well_yield.available} color="#0369a1" />
              </div>
            </Suspense>

            <WellsTable wells={nearby.wells} caps={nearby.capabilities} selectedId={s.selectedWellId}
                        onSelect={(id) => { a.selectWell(id); window.scrollTo({ top: 0, behavior: 'auto' }) }} onDetails={a.openDetails} />
            <Disclaimer />
          </div>
        )
      )}
    </div>
  )
}
