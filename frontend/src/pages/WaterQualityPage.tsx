import { useEffect, useMemo, useState } from 'react'
import { fmtCoord, fmtDate, fmtNumber, plural } from '../lib/format'
import { useActions, useAppState, useHealth } from '../state/AppContext'
import LoadingState from '../components/LoadingState'
import QualityTable from '../components/QualityTable'
import { Disclaimer, EmptyState, ErrorState, Notice, PageTitle } from '../components/ui'

export default function WaterQualityPage({ active }: { active: boolean }) {
  const { analysis, quality } = useAppState()
  const a = useActions()
  const health = useHealth()
  const [param, setParam] = useState('all')

  // load lazily: the quality query only runs once this tab is opened for an analysed location
  useEffect(() => {
    if (active) void a.loadQuality()
  }, [active, analysis, a])

  const data = quality.status === 'success' ? quality.data : null
  const rows = useMemo(
    () => (data ? data.measurements.filter((m) => param === 'all' || m.parameter === param) : []),
    [data, param],
  )
  useEffect(() => setParam('all'), [data])

  return (
    <div className="space-y-5">
      <PageTitle title="Historical water quality">Explore available water-quality observations from nearby wells.</PageTitle>
      <Disclaimer kind="quality" />

      {analysis.status !== 'success' && (
        <EmptyState title="Choose a location first">
          <p>Water-quality records are shown for the location you analyze on the Explore Property tab.</p>
          <button type="button" className="btn btn-primary mt-3" onClick={() => a.setTab('explore')}>Go to Explore Property</button>
        </EmptyState>
      )}

      {analysis.status === 'success' && (
        <>
          <p className="text-slate-800">
            Selected location: <strong className="tabular-nums">{fmtCoord(analysis.data.nearby.location)}</strong>
            {' · '}search radius <strong>{analysis.data.nearby.radius_km} km</strong>
          </p>

          {health && !health.features.quality && (
            <EmptyState title="Water-quality data is not available">
              This dataset has no water-quality table mapped, so no measurements can be shown.
            </EmptyState>
          )}

          {quality.status === 'loading' && <LoadingState label="Loading water-quality records…" />}
          {quality.status === 'error' && <ErrorState message={quality.message} onRetry={() => void a.loadQuality()} />}

          {data && data.available && (
            <>
              {data.total_records === 0 ? (
                <EmptyState title="No data">{data.explanation ?? 'No water-quality measurements are available for this selection.'}</EmptyState>
              ) : (
                <>
                  <section className="panel p-4" aria-label="Water-quality summary">
                    <h2 className="text-xl font-semibold">
                      {plural(data.total_records, 'measurement')} found
                    </h2>
                    {data.returned_records < data.total_records && (
                      <p className="text-slate-700">Showing the {fmtNumber(data.returned_records, 0)} most recent.</p>
                    )}
                    <ul className="mt-3 flex flex-wrap gap-2">
                      {data.parameters.map((p) => (
                        <li key={p.parameter}>
                          <button
                            type="button" aria-pressed={param === p.parameter}
                            onClick={() => setParam(param === p.parameter ? 'all' : p.parameter)}
                            className={`min-h-[44px] rounded-full border px-3 text-left ${param === p.parameter ? 'border-teal-700 bg-teal-700 text-white' : 'border-slate-300 bg-white hover:bg-slate-50'}`}
                          >
                            <span className="font-medium">{p.parameter}</span>
                            <span className="ml-2 text-sm opacity-90">{p.observations} obs · {plural(p.wells, 'well')}{p.latest_sample_date ? ` · latest ${fmtDate(p.latest_sample_date)}` : ''}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                    <p className="mt-2 text-sm text-slate-600">Only parameters that appear in the source records are listed. Select one to filter the table.</p>
                  </section>

                  {data.guideline.configured ? (
                    <Notice>
                      Guideline comparisons use: <strong>{[data.guideline.reference, data.guideline.version].filter(Boolean).join(' ')}</strong>.
                      Measurements with a different unit or no matching guideline are marked “Not evaluated”.
                    </Notice>
                  ) : (
                    <Notice>
                      No reference guideline is configured for this deployment, so measurements are shown <strong>without comparison</strong> and are marked “Not evaluated”.
                    </Notice>
                  )}

                  <QualityTable rows={rows} onWell={a.openDetails} />
                </>
              )}
            </>
          )}
          {data && !data.available && <EmptyState title="Water-quality data is not available">{data.explanation}</EmptyState>}

          <section className="panel space-y-3 p-4">
            <h2 className="text-xl font-semibold">Reading these results</h2>
            <p><strong>What the statuses mean.</strong> “Within guideline” and “Above guideline” compare one recorded value with the configured reference value. “Not evaluated” means no suitable guideline or matching unit was available. “No data” means no usable number was recorded.</p>
            <p><strong>Why you should still test.</strong> A neighbour’s well can differ from yours, and water chemistry changes over time. Only a laboratory test of your own water tells you what is in it.</p>
            <p><strong>Data limitations.</strong> Records are historical, collected for different purposes, and may be incomplete. Values shown “as recorded” (for example below a detection limit) could not be read as a plain number.</p>
          </section>
          <Disclaimer kind="quality" />
        </>
      )}
    </div>
  )
}
