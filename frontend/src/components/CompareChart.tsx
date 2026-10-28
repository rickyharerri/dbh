import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from 'recharts'
import { fmtNumber, unitName } from '../lib/format'
import { EmptyState } from './ui'

/** Two bars (A vs B) for a single metric. Values are medians; sample sizes are in the labels. */
export default function CompareChart({ title, unit, a, b, aN, bN }: {
  title: string; unit: string | null; a: number | null; b: number | null; aN: number; bN: number
}) {
  const u = unitName(unit)
  const hasAny = a !== null || b !== null
  const data = [
    { name: `A (n=${aN})`, value: a ?? 0, missing: a === null, color: '#1d4ed8' },
    { name: `B (n=${bN})`, value: b ?? 0, missing: b === null, color: '#b45309' },
  ]
  const summary = `${title}: Property A ${a === null ? 'not available' : `${fmtNumber(a)} ${u ?? ''}`.trim()}, Property B ${b === null ? 'not available' : `${fmtNumber(b)} ${u ?? ''}`.trim()}.`
  return (
    <figure className="panel p-4">
      <figcaption className="mb-2 text-lg font-semibold">{title}{u ? ` (${u})` : ''}</figcaption>
      {!hasAny ? (
        <EmptyState title="No measurements">Neither property has a recorded value to chart.</EmptyState>
      ) : (
        <div role="img" aria-label={summary} className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 20, right: 8, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 13 }} />
              <YAxis tick={{ fontSize: 12 }} width={44} />
              <Bar dataKey="value" isAnimationActive={false}>
                {data.map((d) => <Cell key={d.name} fill={d.missing ? '#e2e8f0' : d.color} />)}
                <LabelList dataKey="value" position="top" formatter={(v: number) => (v === 0 ? 'n/a' : fmtNumber(v))} fontSize={13} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <p className="mt-1 text-sm text-slate-700">{summary} Bars show medians; n is the number of wells with a recorded value.</p>
    </figure>
  )
}
