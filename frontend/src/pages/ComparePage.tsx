import { lazy, Suspense } from 'react'
import { fmtCoord, fmtDate, fmtMeasure, fmtNumber, NOT_AVAILABLE } from '../lib/format'
import { searchKey, useActions, useAppState } from '../state/AppContext'
import CoordinateFields from '../components/CoordinateFields'
import LazyMap from '../components/LazyMap'
import LoadingState, { Spinner } from '../components/LoadingState'
import RadiusPicker from '../components/RadiusPicker'
import { Disclaimer, ErrorState, Notice, PageTitle } from '../components/ui'
import type { CompareResponse, CompareRow, LatLng } from '../types/groundwater'

const CompareChart = lazy(() => import('../components/CompareChart'))
const COLORS = { a: '#1d4ed8', b: '#b45309' }

function cell(r: CompareRow, side: 'a' | 'b'): { text: string; n?: string } {
  const v = side === 'a' ? r.a : r.b
  const n = side === 'a' ? r.a_samples : r.b_samples
  if (!r.available) return { text: NOT_AVAILABLE }
  if (v === null || v === undefined) return { text: NOT_AVAILABLE, n: n !== null && n !== undefined ? `n = ${n}` : undefined }
  if (typeof v === 'string') return { text: r.key === 'latest_record_date' ? fmtDate(v) : v }
  const text = r.unit ? fmtMeasure(v, r.unit) : fmtNumber(v, 1)
  return { text, n: n !== null && n !== undefined ? `n = ${fmtNumber(n, 0)}` : undefined }
}

function Results({ res }: { res: CompareResponse }) {
  const row = (k: string) => res.rows.find((r) => r.key === k)
  const depth = row('depth'), yld = row('well_yield')
  return (
    <div className="space-y-5">
      <h2 className="text-xl font-semibold">Comparison within {res.radius_km} km of each property</h2>

      <div className="panel overflow-x-auto">
        <table className="w-full min-w-[560px] text-left">
          <caption className="sr-only">Side-by-side comparison of Property A and Property B, search radius {res.radius_km} km</caption>
          <thead className="bg-slate-50 text-sm">
            <tr>
              <th scope="col" className="px-4 py-2">Measure</th>
              <th scope="col" className="px-2 py-2 text-blue-800">Property A</th>
              <th scope="col" className="px-2 py-2 text-amber-800">Property B</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {res.rows.map((r) => {
              const a = cell(r, 'a'), b = cell(r, 'b')
              return (
                <tr key={r.key}>
                  <th scope="row" className="px-4 py-2 font-medium">{r.label}</th>
                  {[a, b].map((c, i) => (
                    <td key={i} className="px-2 py-2 tabular-nums">
                      {c.text}
                      {c.n && <span className="ml-2 text-sm text-slate-600">({c.n})</span>}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <Suspense fallback={<div role="status" className="h-60 animate-pulse rounded-lg bg-slate-100" aria-label="Loading charts" />}>
      <div className="grid gap-4 lg:grid-cols-2">
        {depth?.available && (
          <CompareChart title="Typical well depth" unit={depth.unit} a={res.property_a.depth.median} b={res.property_b.depth.median}
                        aN={res.property_a.depth.sample_count} bN={res.property_b.depth.sample_count} />
        )}
        {yld?.available && (
          <CompareChart title="Typical well yield" unit={yld.unit} a={res.property_a.well_yield.median} b={res.property_b.well_yield.median}
                        aN={res.property_a.well_yield.sample_count} bN={res.property_b.well_yield.sample_count} />
        )}
      </div>
      </Suspense>

      <section className="panel p-4" aria-label="Plain-language summary">
        <h3 className="mb-1 text-lg font-semibold">In plain language</h3>
        <p className="max-w-3xl">{res.summary_text}</p>
      </section>
      <Disclaimer />
    </div>
  )
}

export default function ComparePage({ active }: { active: boolean }) {
  const { compare } = useAppState()
  const a = useActions()
  const { a: locA, b: locB, radiusKm, picking, result } = compare
  const ready = locA !== null && locB !== null
  const stale = result.status === 'success' && ready && result.key !== `${searchKey(locA!, radiusKm)}|${searchKey(locB!, radiusKm)}`

  const onPick = (p: LatLng) => {
    a.setCompareLocation(picking, p)
    if (picking === 'a' && !locB) a.setComparePicking('b') // natural flow: A, then B
  }

  const points = [
    ...(locA ? [{ key: 'a', label: 'Property A', location: locA, color: COLORS.a }] : []),
    ...(locB ? [{ key: 'b', label: 'Property B', location: locB, color: COLORS.b }] : []),
  ]

  return (
    <div className="space-y-5">
      <PageTitle title="Compare two properties">Choose two locations and see how their nearby historical wells compare.</PageTitle>

      <section className="panel space-y-4 p-4" aria-label="Choose properties">
        <fieldset>
          <legend className="mb-1 text-base font-semibold text-slate-800">Click the map to set</legend>
          <div className="flex flex-wrap gap-2">
            {(['a', 'b'] as const).map((w) => (
              <label key={w} className="cursor-pointer">
                <input type="radio" name="compare-picking" className="peer sr-only" checked={picking === w} onChange={() => a.setComparePicking(w)} />
                <span className="inline-flex min-h-[44px] items-center rounded-md border border-slate-300 px-4 text-base font-medium peer-checked:border-slate-900 peer-checked:bg-slate-900 peer-checked:text-white peer-focus-visible:outline peer-focus-visible:outline-[3px] peer-focus-visible:outline-offset-2 peer-focus-visible:outline-sky-700">
                  Property {w.toUpperCase()}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="grid gap-5 md:grid-cols-2">
          <CoordinateFields legend="Property A coordinates" value={locA} onCommit={(p) => a.setCompareLocation('a', p, { recentre: true })} />
          <CoordinateFields legend="Property B coordinates" value={locB} onCommit={(p) => a.setCompareLocation('b', p, { recentre: true })} />
        </div>
        <RadiusPicker name="compare-radius" value={radiusKm} onChange={a.setCompareRadius} />

        <div className="flex flex-wrap items-center gap-3">
          <button type="button" className="btn btn-primary" disabled={!ready || result.status === 'loading'} onClick={() => void a.runCompare()}>
            {result.status === 'loading' ? <><Spinner /> Comparing…</> : 'Compare Properties'}
          </button>
          {!ready && <p role="status" className="text-slate-700">Set both Property A and Property B to compare.</p>}
          {ready && <p role="status" className="text-slate-800">A: <span className="tabular-nums">{fmtCoord(locA!)}</span> · B: <span className="tabular-nums">{fmtCoord(locB!)}</span> · radius {radiusKm} km</p>}
        </div>
        {stale && <p role="status" className="text-sm text-amber-900">A location or the radius changed. Select “Compare Properties” to update the results.</p>}
      </section>

      <LazyMap
        points={points} radiusKm={radiusKm} onPick={onPick}
        focusNonce={compare.focusNonce} active={active}
      />

      {result.status === 'loading' && <LoadingState label="Comparing both locations… this can take a few seconds." />}
      {result.status === 'error' && <ErrorState message={result.message} details={result.missing} onRetry={result.code === 'not_configured' ? undefined : () => void a.runCompare()} />}
      {result.status === 'idle' && <Notice>Both properties use the same search radius and the same measurement definitions, so the results are directly comparable.</Notice>}
      {result.status === 'success' && <Results res={result.data} />}
    </div>
  )
}
