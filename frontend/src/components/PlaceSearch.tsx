import { useId, useState } from 'react'
import { api, ApiError } from '../services/api'
import type { GeocodeResult, LatLng } from '../types/groundwater'
import { Spinner } from './LoadingState'

/** Only rendered when the backend reports a configured geocoder. */
export default function PlaceSearch({ onPick }: { onPick: (p: LatLng) => void }) {
  const id = useId()
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [results, setResults] = useState<GeocodeResult[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const search = async (e: React.FormEvent) => {
    e.preventDefault()
    if (q.trim().length < 2) return
    setBusy(true); setError(null)
    try {
      setResults((await api.geocode(q.trim())).results)
    } catch (err) {
      setResults(null)
      setError(err instanceof ApiError ? err.message : 'Place search failed. Try coordinates instead.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={search} className="space-y-2">
      <label htmlFor={id} className="block text-base font-semibold text-slate-800">Search for a place in Alberta</label>
      <div className="flex gap-2">
        <input id={id} className="field" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Town, road or address" />
        <button type="submit" className="btn btn-secondary" disabled={busy}>{busy ? <Spinner /> : 'Search'}</button>
      </div>
      {error && <p role="alert" className="text-sm text-red-800">{error}</p>}
      {results && results.length === 0 && <p role="status" className="text-sm text-slate-700">No places found in Alberta. Try another name.</p>}
      {results && results.length > 0 && (
        <ul className="divide-y divide-slate-200 rounded-md border border-slate-200">
          {results.map((r, i) => (
            <li key={i}>
              <button type="button" className="min-h-[44px] w-full px-3 py-2 text-left hover:bg-slate-50"
                      onClick={() => { onPick({ latitude: r.latitude, longitude: r.longitude }); setResults(null) }}>
                {r.name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </form>
  )
}
