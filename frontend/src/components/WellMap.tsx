import { useEffect, useMemo } from 'react'
import L from 'leaflet'
import { Circle, CircleMarker, MapContainer, Popup, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { fmtDate, fmtMeasure, NOT_AVAILABLE, round5 } from '../lib/format'
import type { LatLng, Units, Well } from '../types/groundwater'
import WellMarker from './WellMarker'

export interface MapPoint { key: string; label: string; location: LatLng; color: string }

export interface WellMapProps {
  points: MapPoint[]
  radiusKm: number
  wells?: Well[]
  units?: Units
  selectedWellId?: string | null
  selectNonce?: number
  onPick: (p: LatLng) => void
  onSelectWell?: (id: string) => void
  onViewDetails?: (id: string) => void
  /** increments when the map should re-centre on the points (typed coordinates, new analysis) */
  focusNonce: number
  /** false while this tab is hidden; Leaflet needs a size refresh when it becomes visible again */
  active: boolean
  height?: string
}

// Alberta, padded so the whole province can be panned into view but not the whole world.
const MAX_BOUNDS: L.LatLngBoundsExpression = [[47.5, -122.5], [61.5, -107.5]]
const ALBERTA_CENTRE: L.LatLngExpression = [54.5, -114.5]

function ClickToPick({ onPick }: { onPick: (p: LatLng) => void }) {
  useMapEvents({ click: (e) => onPick({ latitude: round5(e.latlng.lat), longitude: round5(e.latlng.lng) }) })
  return null
}

function ViewController({ points, radiusKm, focusNonce, active }: Pick<WellMapProps, 'points' | 'radiusKm' | 'focusNonce' | 'active'>) {
  const map = useMap()
  useEffect(() => {
    if (!active) return
    const t = setTimeout(() => map.invalidateSize(), 0)
    return () => clearTimeout(t)
  }, [active, map])

  useEffect(() => {
    if (!active || points.length === 0) return
    const bounds = L.latLngBounds([])
    for (const p of points) {
      // toBounds takes the full side length in metres and needs no map instance (unlike Circle#getBounds)
      bounds.extend(L.latLng(p.location.latitude, p.location.longitude).toBounds(radiusKm * 2000))
    }
    map.fitBounds(bounds, { padding: [24, 24], maxZoom: 14, animate: false })
    // deliberately keyed on focusNonce only: plain map clicks must not re-zoom under the user's cursor
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusNonce, active])
  return null
}

export default function WellMap(props: WellMapProps) {
  const { points, radiusKm, wells = [], units, selectedWellId, selectNonce = 0, onPick, onSelectWell, onViewDetails } = props
  const selected = useMemo(() => wells.find((w) => w.well_id === selectedWellId) ?? null, [wells, selectedWellId])

  return (
    <div className="overflow-hidden rounded-lg border border-slate-300">
      <MapContainer
        center={ALBERTA_CENTRE}
        zoom={6}
        minZoom={5}
        maxBounds={MAX_BOUNDS}
        maxBoundsViscosity={0.8}
        preferCanvas
        className={props.height ?? 'h-[340px] sm:h-[460px]'}
        aria-label="Map of Alberta. Click to choose a location."
      >
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <ClickToPick onPick={onPick} />
        <ViewController points={points} radiusKm={radiusKm} focusNonce={props.focusNonce} active={props.active} />

        {points.map((p) => (
          <Circle
            key={`r-${p.key}`}
            center={[p.location.latitude, p.location.longitude]}
            radius={radiusKm * 1000}
            interactive={false}
            pathOptions={{ color: p.color, weight: 2, fillColor: p.color, fillOpacity: 0.07, dashArray: '6 6' }}
          />
        ))}

        {wells.map((w) => (
          <WellMarker key={w.well_id} well={w} selected={w.well_id === selectedWellId} onSelect={onSelectWell ?? (() => {})} />
        ))}

        {points.map((p) => (
          <CircleMarker
            key={`p-${p.key}`}
            center={[p.location.latitude, p.location.longitude]}
            radius={9}
            bubblingMouseEvents={false}
            pathOptions={{ color: '#fff', weight: 3, fillColor: p.color, fillOpacity: 1 }}
          >
            <Tooltip permanent direction="top" offset={[0, -8]}>{p.label}</Tooltip>
          </CircleMarker>
        ))}

        {selected && (
          <Popup key={`${selected.well_id}-${selectNonce}`} position={[selected.latitude, selected.longitude]} autoPan>
            <div className="min-w-[180px] space-y-1 text-sm text-slate-800">
              <p className="text-base font-semibold">Well {selected.well_id}</p>
              <p>Depth: {fmtMeasure(selected.depth, units?.depth)}</p>
              <p>Yield: {fmtMeasure(selected.well_yield, units?.well_yield)}</p>
              <p>Drilled: {selected.drilling_date ? fmtDate(selected.drilling_date) : NOT_AVAILABLE}</p>
              <p className="text-xs text-slate-600">Historical record, {selected.distance_km.toFixed(2)} km away</p>
              {onViewDetails && (
                <button type="button" className="btn btn-primary !min-h-[40px] w-full" onClick={() => onViewDetails(selected.well_id)}>
                  View details
                </button>
              )}
            </div>
          </Popup>
        )}
      </MapContainer>
    </div>
  )
}
