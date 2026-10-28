import type { ReactNode } from 'react'
import { InfoTip } from './ui'

interface Props {
  title: string
  tip: string
  /** big figure; pass null when the source has no value (renders "Not available", never 0) */
  value: ReactNode | null
  /** plain-language sentence under the figure */
  description?: ReactNode
  /** sample size / basis, always shown when there is a figure */
  basis?: ReactNode
  unavailableReason?: string
}

export default function SummaryCard({ title, tip, value, description, basis, unavailableReason }: Props) {
  const has = value !== null && value !== undefined
  return (
    <section className="panel flex flex-col p-4" aria-label={title}>
      <h3 className="flex items-center gap-1 text-base font-semibold text-slate-800">
        {title}
        <InfoTip text={tip} label={title} />
      </h3>
      {has ? (
        <>
          <p className="mt-1 text-3xl font-semibold tabular-nums text-teal-800">{value}</p>
          {description && <p className="mt-1 text-slate-800">{description}</p>}
          {basis && <p className="mt-auto pt-2 text-sm text-slate-600">{basis}</p>}
        </>
      ) : (
        <>
          <p className="mt-1 text-2xl font-semibold text-slate-600">Not available</p>
          <p className="mt-1 text-sm text-slate-600">{unavailableReason ?? 'No recorded measurements for this selection.'}</p>
        </>
      )}
    </section>
  )
}
