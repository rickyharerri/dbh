import { RADII, type Radius } from '../types/groundwater'

export default function RadiusPicker({ value, onChange, name }: { value: Radius; onChange: (r: Radius) => void; name: string }) {
  return (
    <fieldset>
      <legend className="mb-1 text-base font-semibold text-slate-800">Search radius</legend>
      <div className="flex flex-wrap gap-2">
        {RADII.map((r) => (
          <label key={r} className="cursor-pointer">
            <input
              type="radio" name={name} value={r} checked={value === r} onChange={() => onChange(r)}
              className="peer sr-only"
            />
            <span className="inline-flex min-h-[44px] min-w-[64px] items-center justify-center rounded-md border border-slate-300 bg-white px-3 text-base font-medium text-slate-800 peer-checked:border-teal-700 peer-checked:bg-teal-700 peer-checked:text-white peer-focus-visible:outline peer-focus-visible:outline-[3px] peer-focus-visible:outline-offset-2 peer-focus-visible:outline-sky-700">
              {r} km
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  )
}
