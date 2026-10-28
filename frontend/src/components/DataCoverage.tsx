import { fmtDate, fmtNumber } from '../lib/format'
import type { SummaryResponse } from '../types/groundwater'
import { Notice } from './ui'

/** FR-008: how much historical data stands behind the numbers. */
export default function DataCoverage({ s }: { s: SummaryResponse }) {
  const rows: [string, string][] = [
    ['Wells in the search area', fmtNumber(s.total_wells, 0)],
    ...(s.depth.available ? [['Wells with a recorded depth', fmtNumber(s.depth.sample_count, 0)] as [string, string]] : []),
    ...(s.well_yield.available ? [['Wells with a recorded yield', fmtNumber(s.well_yield.sample_count, 0)] as [string, string]] : []),
    ...(s.quality.available ? [['Wells with water-quality records', fmtNumber(s.quality.wells_with_quality, 0)] as [string, string]] : []),
    ['Latest drilling date on record', fmtDate(s.latest_record_date)],
  ]
  return (
    <section aria-label="Data availability" className="space-y-3">
      {s.limited_data && s.notes.map((n) => <Notice key={n} tone="warn">{n}</Notice>)}
      <div className="panel p-4">
        <h3 className="mb-2 text-base font-semibold">How much data supports these numbers</h3>
        <dl className="grid gap-x-6 gap-y-1 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 border-b border-slate-100 py-1">
              <dt className="text-slate-700">{k}</dt>
              <dd className="font-medium tabular-nums">{v}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}
