import type { LatLng } from '../types/groundwater'

export const NOT_AVAILABLE = 'Not available'

const UNIT_NAMES: Record<string, string> = {
  m: 'metres',
  ft: 'feet',
  gpm: 'gallons per minute',
  igpm: 'imperial gallons per minute',
  'l/min': 'litres per minute',
  lpm: 'litres per minute',
  'mg/l': 'mg/L',
}

/** Plain-language unit name when we know one, otherwise the source unit exactly as recorded. */
export function unitName(unit: string | null | undefined): string | null {
  if (!unit) return null
  return UNIT_NAMES[unit.trim().toLowerCase()] ?? unit
}

export function fmtNumber(value: number | null | undefined, maxDigits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return NOT_AVAILABLE
  return value.toLocaleString('en-CA', { maximumFractionDigits: maxDigits })
}

/** "75 metres" — or "75 (unit not recorded)" when the dataset mapping has no unit. Never 0 for missing. */
export function fmtMeasure(value: number | null | undefined, unit: string | null | undefined, maxDigits = 1): string {
  if (value === null || value === undefined) return NOT_AVAILABLE
  const n = fmtNumber(value, maxDigits)
  const u = unitName(unit)
  return u ? `${n} ${u}` : `${n} (unit not recorded)`
}

export function fmtDate(value: string | null | undefined): string {
  if (!value) return NOT_AVAILABLE
  const d = new Date(value.length === 10 ? `${value}T00:00:00` : value)
  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })
}

export function fmtCoord(p: LatLng): string {
  return `${p.latitude.toFixed(5)}, ${p.longitude.toFixed(5)}`
}

export const round5 = (n: number) => Math.round(n * 1e5) / 1e5

// Rough bounding box of Alberta — used only for a gentle warning, never to block a request.
export function inAlberta(p: LatLng): boolean {
  return p.latitude >= 48.99 && p.latitude <= 60.01 && p.longitude >= -120.01 && p.longitude <= -109.99
}

export function parseCoordinate(raw: string, kind: 'lat' | 'lon'): { value?: number; error?: string } {
  const text = raw.trim()
  if (text === '') return { error: `Enter a ${kind === 'lat' ? 'latitude' : 'longitude'}.` }
  const n = Number(text)
  if (!Number.isFinite(n)) return { error: `${kind === 'lat' ? 'Latitude' : 'Longitude'} must be a number.` }
  const [min, max] = kind === 'lat' ? [-90, 90] : [-180, 180]
  if (n < min || n > max) {
    return { error: `${kind === 'lat' ? 'Latitude' : 'Longitude'} must be between ${min} and ${max}.` }
  }
  return { value: round5(n) }
}

export const plural = (n: number, one: string, many = `${one}s`) => `${n.toLocaleString('en-CA')} ${n === 1 ? one : many}`
