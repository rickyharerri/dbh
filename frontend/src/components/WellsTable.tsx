import { useState } from 'react'
import { fmtDate, fmtNumber, NOT_AVAILABLE, unitName } from '../lib/format'
import type { Capabilities, Well } from '../types/groundwater'

const PAGE = 25

export default function WellsTable({ wells, caps, selectedId, onSelect, onDetails }: {
  wells: Well[]; caps: Capabilities; selectedId: string | null
  onSelect: (id: string) => void; onDetails: (id: string) => void
}) {
  const [shown, setShown] = useState(PAGE)
  const u = caps.units
  const head = (label: string, unit: string | null) => (unit ? `${label} (${unitName(unit)})` : label)
  const cell = (v: number | null) => (v === null ? NOT_AVAILABLE : fmtNumber(v))

  return (
    <div className="panel">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-left">
          <caption className="p-4 pb-2 text-left text-lg font-semibold">
            Nearby wells <span className="text-base font-normal text-slate-600">(nearest first)</span>
          </caption>
          <thead className="bg-slate-50 text-sm text-slate-700">
            <tr>
              <th scope="col" className="px-4 py-2">Well ID</th>
              <th scope="col" className="px-2 py-2">Distance (km)</th>
              {caps.depth && <th scope="col" className="px-2 py-2">{head('Depth', u.depth)}</th>}
              {caps.well_yield && <th scope="col" className="px-2 py-2">{head('Yield', u.well_yield)}</th>}
              {caps.drilling_date && <th scope="col" className="px-2 py-2">Drilled</th>}
              {caps.status && <th scope="col" className="px-2 py-2">Status</th>}
              <th scope="col" className="px-4 py-2"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {wells.slice(0, shown).map((w) => (
              <tr key={w.well_id} className={w.well_id === selectedId ? 'bg-amber-50' : undefined}>
                <th scope="row" className="px-4 py-2 font-medium">{w.well_id}</th>
                <td className="px-2 py-2 tabular-nums">{w.distance_km.toFixed(2)}</td>
                {caps.depth && <td className="px-2 py-2 tabular-nums">{cell(w.depth)}</td>}
                {caps.well_yield && <td className="px-2 py-2 tabular-nums">{cell(w.well_yield)}</td>}
                {caps.drilling_date && <td className="px-2 py-2">{fmtDate(w.drilling_date)}</td>}
                {caps.status && <td className="px-2 py-2">{w.status ?? NOT_AVAILABLE}</td>}
                <td className="px-4 py-2 text-right">
                  <div className="flex justify-end gap-2">
                    <button type="button" className="btn btn-secondary !min-h-[40px] !px-3" onClick={() => onSelect(w.well_id)}
                            aria-label={`Show well ${w.well_id} on the map`}>On map</button>
                    <button type="button" className="btn btn-secondary !min-h-[40px] !px-3" onClick={() => onDetails(w.well_id)}
                            aria-label={`View details for well ${w.well_id}`}>Details</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {shown < wells.length && (
        <div className="border-t border-slate-200 p-3 text-center">
          <button type="button" className="btn btn-secondary" onClick={() => setShown((n) => n + PAGE * 4)}>
            Show more ({wells.length - shown} remaining)
          </button>
        </div>
      )}
    </div>
  )
}
