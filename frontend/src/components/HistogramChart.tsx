import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { fmtNumber, unitName } from '../lib/format'
import type { Histogram } from '../types/groundwater'
import { EmptyState } from './ui'

/** Distribution chart. Always has a text summary + data table for screen readers. */
export default function HistogramChart({ title, noun, histogram, available, color }: {
  title: string
  /** e.g. "depth" — used in the text summary */
  noun: string
  histogram: Histogram
  available: boolean
  color: string
}) {
  const unit = unitName(histogram.unit)
  const axis = unit ? `${title} (${unit})` : title
  const n = histogram.sample_count

  let body
  if (!available) {
    body = <EmptyState title="Not available">This dataset has no {noun} measurements.</EmptyState>
  } else if (n === 0 || histogram.bins.length === 0) {
    body = <EmptyState title="No measurements">No {noun} was recorded for wells in this area, so there is nothing to chart.</EmptyState>
  } else {
    const top = histogram.bins.reduce((a, b) => (b.count > a.count ? b : a))
    const summary = `${fmtNumber(n, 0)} wells have a recorded ${noun}. The most common range is ${top.label}${unit ? ` ${unit}` : ''}, with ${fmtNumber(top.count, 0)} wells.`
    body = (
      <>
        <div role="img" aria-label={summary} className="h-60">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={histogram.bins} margin={{ top: 8, right: 8, bottom: 28, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} interval="preserveStartEnd" label={{ value: axis, position: 'insideBottom', offset: -18, fontSize: 13 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 12 }} width={44} label={{ value: 'Wells', angle: -90, position: 'insideLeft', fontSize: 13 }} />
              <Tooltip formatter={(v: number) => [`${v} wells`, 'Count']} labelFormatter={(l) => `${l}${unit ? ` ${unit}` : ''}`} />
              <Bar dataKey="count" fill={color} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-1 text-sm text-slate-700">{summary}</p>
        <table className="sr-only">
          <caption>{title} distribution</caption>
          <thead><tr><th>Range{unit ? ` (${unit})` : ''}</th><th>Wells</th></tr></thead>
          <tbody>{histogram.bins.map((b) => <tr key={b.label}><td>{b.label}</td><td>{b.count}</td></tr>)}</tbody>
        </table>
      </>
    )
  }
  return (
    <figure className="panel p-4">
      <figcaption className="mb-2 text-lg font-semibold">{title} distribution</figcaption>
      {body}
    </figure>
  )
}
