import { useEffect, useState } from 'react'
import { fmtCoord, fmtDate, fmtMeasure, NOT_AVAILABLE } from '../lib/format'
import { api, ApiError } from '../services/api'
import type { WellDetails as Details } from '../types/groundwater'
import Dialog from './Dialog'
import LoadingState from './LoadingState'
import QualityTable from './QualityTable'
import { Disclaimer, ErrorState } from './ui'

/** FR-007: side panel for one historical well. Only fields the dataset supports are shown. */
export default function WellDetails({ wellId, onClose }: { wellId: string | null; onClose: () => void }) {
  const [state, setState] = useState<{ id: string; data?: Details; error?: string } | null>(null)

  useEffect(() => {
    if (!wellId) return
    let live = true
    setState(null)
    api.wellDetails(wellId)
      .then((data) => live && setState({ id: wellId, data }))
      .catch((e) => live && setState({ id: wellId, error: e instanceof ApiError ? e.message : 'We couldn’t load this well. Please try again.' }))
    return () => { live = false }
  }, [wellId])

  const d = state?.data
  const row = (label: string, value: string) => (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-2">
      <dt className="text-slate-700">{label}</dt>
      <dd className="text-right font-medium">{value}</dd>
    </div>
  )

  return (
    <Dialog open={!!wellId} onClose={onClose} title={wellId ? `Well ${wellId}` : 'Well'} side>
      {!state && <LoadingState label="Loading well details…" />}
      {state?.error && <ErrorState message={state.error} />}
      {d && (
        <div className="space-y-4">
          <p className="rounded-md bg-slate-50 p-2 text-sm text-slate-700">
            This is a <strong>historical record</strong>, not a current measurement.
            {d.data_source === 'demo' && <strong className="text-amber-900"> Demo data: synthetic, not a real well.</strong>}
          </p>
          <dl>
            {row('Location', fmtCoord(d))}
            {d.capabilities.drilling_date && row('Drilling date', fmtDate(d.drilling_date))}
            {d.capabilities.depth && row('Well depth', fmtMeasure(d.depth, d.units.depth))}
            {d.capabilities.well_yield && row('Recorded yield', fmtMeasure(d.well_yield, d.units.well_yield))}
            {d.capabilities.static_water_level && row('Recorded water level (below ground)', fmtMeasure(d.static_water_level, d.units.static_water_level))}
            {d.capabilities.status && row('Status', d.status ?? NOT_AVAILABLE)}
          </dl>

          {d.capabilities.quality && (
            <section>
              <h3 className="mb-2 text-lg font-semibold">Water-quality observations</h3>
              {d.quality.length === 0
                ? <p className="text-slate-700">No water-quality measurements are recorded for this well.</p>
                : <QualityTable rows={d.quality} showWell={false} />}
              <div className="mt-3"><Disclaimer kind="quality" /></div>
            </section>
          )}

          <p className="text-sm text-slate-600">
            Geological information is not shown because it is not part of the connected dataset mapping.
          </p>
          <p className="text-sm text-slate-600">Source dataset: {d.source_dataset ?? NOT_AVAILABLE}</p>
        </div>
      )}
    </Dialog>
  )
}
