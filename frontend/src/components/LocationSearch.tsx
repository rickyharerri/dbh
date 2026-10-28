import { fmtCoord } from '../lib/format'
import { searchKey, useActions, useAppState, useHealth } from '../state/AppContext'
import CoordinateFields from './CoordinateFields'
import { Spinner } from './LoadingState'
import PlaceSearch from './PlaceSearch'
import RadiusPicker from './RadiusPicker'

/** Explore-page controls: place search (if configured), coordinates, radius, and the Analyze button. */
export default function LocationSearch() {
  const { location, radiusKm, analysis } = useAppState()
  const { setLocation, setRadius, analyze } = useActions()
  const health = useHealth()
  const loading = analysis.status === 'loading'
  const stale = analysis.status === 'success' && location !== null && analysis.key !== searchKey(location, radiusKm)

  return (
    <section className="panel space-y-4 p-4" aria-label="Choose a location">
      {health?.features.geocoding ? (
        <PlaceSearch onPick={(p) => setLocation(p, { recentre: true })} />
      ) : (
        <p className="text-slate-700">
          <strong>Click the map</strong> to choose a location, or type coordinates below.
        </p>
      )}
      <CoordinateFields legend="Latitude and longitude" value={location} onCommit={(p) => setLocation(p, { recentre: true })} />
      <RadiusPicker name="explore-radius" value={radiusKm} onChange={setRadius} />

      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className="btn btn-primary" disabled={!location || loading} onClick={() => void analyze()}>
          {loading ? <><Spinner /> Analyzing…</> : 'Analyze Groundwater'}
        </button>
        <p role="status" className="text-slate-800">
          {location ? <>Selected location: <strong className="tabular-nums">{fmtCoord(location)}</strong></> : 'No location selected yet.'}
        </p>
      </div>
      {stale && <p role="status" className="text-sm text-amber-900">The location or radius changed. Select “Analyze Groundwater” to update the results.</p>}
    </section>
  )
}
