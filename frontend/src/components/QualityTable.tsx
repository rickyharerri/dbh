import { useState } from 'react'
import { fmtDate, fmtNumber, NOT_AVAILABLE } from '../lib/format'
import type { QualityMeasurement, QualityStatus } from '../types/groundwater'

const STATUS: Record<QualityStatus, { label: string; icon: string; cls: string }> = {
  within_guideline: { label: 'Within guideline', icon: '✓', cls: 'border-green-300 bg-green-50 text-green-900' },
  above_guideline: { label: 'Above guideline', icon: '▲', cls: 'border-red-300 bg-red-50 text-red-900' },
  not_evaluated: { label: 'Not evaluated', icon: '–', cls: 'border-slate-300 bg-slate-100 text-slate-800' },
  no_data: { label: 'No data', icon: '○', cls: 'border-slate-300 bg-white text-slate-800' },
}

/** Status is always conveyed by words and a symbol, never by colour alone. */
export function StatusBadge({ status }: { status: QualityStatus }) {
  const s = STATUS[status]
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-sm font-medium ${s.cls}`}>
      <span aria-hidden="true">{s.icon}</span>{s.label}
    </span>
  )
}

export function valueText(m: QualityMeasurement): string {
  if (m.value !== null) return `${fmtNumber(m.value, 4)}${m.unit ? ` ${m.unit}` : ''}`
  return m.value_raw ? `${m.value_raw}${m.unit ? ` ${m.unit}` : ''} (as recorded)` : NOT_AVAILABLE
}

export default function QualityTable({ rows, showWell = true, onWell }: {
  rows: QualityMeasurement[]; showWell?: boolean; onWell?: (id: string) => void
}) {
  const [shown, setShown] = useState(25)
  return (
    <div className="panel">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-left">
          <caption className="sr-only">Historical water-quality measurements</caption>
          <thead className="bg-slate-50 text-sm text-slate-700">
            <tr>
              <th scope="col" className="px-4 py-2">Parameter</th>
              <th scope="col" className="px-2 py-2">Recorded value</th>
              <th scope="col" className="px-2 py-2">Reference guideline</th>
              <th scope="col" className="px-2 py-2">Status</th>
              {showWell && <th scope="col" className="px-2 py-2">Well</th>}
              <th scope="col" className="px-2 py-2">Sample date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.slice(0, shown).map((m, i) => (
              <tr key={`${m.well_id}-${m.parameter}-${m.sample_date}-${i}`}>
                <th scope="row" className="px-4 py-2 font-medium">{m.parameter}</th>
                <td className="px-2 py-2 tabular-nums">{valueText(m)}</td>
                <td className="px-2 py-2 text-sm">
                  {m.guideline_value !== null ? (
                    <>
                      <span className="tabular-nums">{fmtNumber(m.guideline_value, 4)} {m.guideline_unit}</span>
                      {m.guideline_reference && <span className="block text-xs text-slate-600">{m.guideline_reference}</span>}
                    </>
                  ) : NOT_AVAILABLE}
                </td>
                <td className="px-2 py-2"><StatusBadge status={m.status} /></td>
                {showWell && (
                  <td className="px-2 py-2">
                    {onWell ? (
                      <button type="button" className="text-sky-800 underline underline-offset-2" onClick={() => onWell(m.well_id)}>{m.well_id}</button>
                    ) : m.well_id}
                  </td>
                )}
                <td className="px-2 py-2">{fmtDate(m.sample_date)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {shown < rows.length && (
        <div className="border-t border-slate-200 p-3 text-center">
          <button type="button" className="btn btn-secondary" onClick={() => setShown((n) => n + 100)}>Show more ({rows.length - shown} remaining)</button>
        </div>
      )}
    </div>
  )
}
