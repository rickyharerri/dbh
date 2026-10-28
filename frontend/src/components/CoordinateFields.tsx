import { useEffect, useId, useState } from 'react'
import { inAlberta, parseCoordinate } from '../lib/format'
import type { LatLng } from '../types/groundwater'

/** Latitude/longitude fallback to map clicking. Invalid values are rejected with a clear message. */
export default function CoordinateFields({ legend, value, onCommit }: {
  legend: string; value: LatLng | null; onCommit: (p: LatLng) => void
}) {
  const id = useId()
  const [lat, setLat] = useState('')
  const [lon, setLon] = useState('')
  const [errors, setErrors] = useState<{ lat?: string; lon?: string }>({})

  // keep the boxes in step with a location chosen by clicking the map
  useEffect(() => {
    if (value) {
      setLat(String(value.latitude))
      setLon(String(value.longitude))
      setErrors({})
    }
  }, [value])

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const a = parseCoordinate(lat, 'lat')
    const b = parseCoordinate(lon, 'lon')
    setErrors({ lat: a.error, lon: b.error })
    if (a.value !== undefined && b.value !== undefined) onCommit({ latitude: a.value, longitude: b.value })
  }

  const outside = value && !inAlberta(value)
  return (
    <form onSubmit={submit} noValidate>
      <fieldset>
        <legend className="mb-1 text-base font-semibold text-slate-800">{legend}</legend>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-start">
          <div>
            <label htmlFor={`${id}-lat`} className="text-sm text-slate-700">Latitude</label>
            <input id={`${id}-lat`} className="field" inputMode="decimal" autoComplete="off" placeholder="e.g. 51.19"
                   value={lat} onChange={(e) => setLat(e.target.value)}
                   aria-invalid={!!errors.lat} aria-describedby={errors.lat ? `${id}-lat-err` : undefined} />
            {errors.lat && <p id={`${id}-lat-err`} role="alert" className="mt-1 text-sm text-red-800">{errors.lat}</p>}
          </div>
          <div>
            <label htmlFor={`${id}-lon`} className="text-sm text-slate-700">Longitude</label>
            <input id={`${id}-lon`} className="field" inputMode="decimal" autoComplete="off" placeholder="e.g. -114.47"
                   value={lon} onChange={(e) => setLon(e.target.value)}
                   aria-invalid={!!errors.lon} aria-describedby={errors.lon ? `${id}-lon-err` : undefined} />
            {errors.lon && <p id={`${id}-lon-err`} role="alert" className="mt-1 text-sm text-red-800">{errors.lon}</p>}
          </div>
          <div className="col-span-2 sm:col-span-1 sm:pt-[22px]">
            <button type="submit" className="btn btn-secondary w-full">Set location</button>
          </div>
        </div>
        {outside && (
          <p className="mt-2 text-sm text-amber-900" role="status">
            This point is outside Alberta, so it will probably have no records.
          </p>
        )}
      </fieldset>
    </form>
  )
}
