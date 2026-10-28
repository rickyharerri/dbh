import { useState } from 'react'
import Dialog from './Dialog'

function Logo() {
  return (
    <svg viewBox="0 0 32 32" className="h-9 w-9 shrink-0" aria-hidden="true">
      <path d="M16 3C16 3 6 14 6 20a10 10 0 0 0 20 0C26 14 16 3 16 3z" fill="#0f766e" />
      <path d="M10.5 20.5c1.6 1.4 3.2 1.4 4.8 0s3.2-1.4 4.8 0 2.2 1 2.4.8" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" fill="none" />
    </svg>
  )
}

export default function Header() {
  const [about, setAbout] = useState(false)
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-3">
          <Logo />
          <div>
            <p className="text-xl font-bold leading-tight text-ink">AquaWise Alberta</p>
            <p className="text-sm text-slate-700 sm:text-base">Understand the water beneath your property.</p>
          </div>
        </div>
        <button type="button" className="btn btn-secondary" onClick={() => setAbout(true)}>About</button>
      </div>

      <Dialog open={about} onClose={() => setAbout(false)} title="About AquaWise Alberta">
        <div className="space-y-3 text-slate-800">
          <p>
            AquaWise Alberta helps you explore <strong>historical</strong> water-well records around a property: how deep
            nearby wells were drilled, how much water they were reported to produce, and which test results were recorded.
          </p>
          <p>The records come from the Alberta Water Well Information Database, hosted in Databricks.</p>
          <p className="rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-950">
            These are records of <em>neighbouring wells</em>, often decades old. They are not a water safety
            certification and do not predict how any individual well will perform. To know what is in your water, have it
            tested by an accredited laboratory.
          </p>
        </div>
      </Dialog>
    </header>
  )
}
