import type {
  CompareResponse, GeocodeResult, GenieChatResponse, Health, LatLng, NearbyResponse, QualityResponse,
  SummaryResponse, WellDetails,
} from '../types/groundwater'

/** All requests go to our own backend (/api/*). No Databricks URL, token or id ever reaches the browser. */
const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''

export class ApiError extends Error {
  constructor(message: string, public code: string, public status: number, public missing: string[] = []) {
    super(message)
    this.name = 'ApiError'
  }
}

// ---- fast repeat lookups: in-memory response cache + de-duplication of identical in-flight requests
const TTL_MS = 5 * 60 * 1000
const cache = new Map<string, { at: number; value: unknown }>()
const inflight = new Map<string, Promise<unknown>>()

export function clearApiCache() {
  cache.clear()
  inflight.clear()
}

async function send<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...init })
  } catch {
    throw new ApiError('We couldn’t reach the AquaWise server. Check your connection and try again.', 'network', 0)
  }
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    /* non-JSON body */
  }
  if (!res.ok) {
    const err = (body as { error?: { code?: string; message?: string; missing?: string[] } } | null)?.error
    throw new ApiError(
      err?.message ?? 'We couldn’t retrieve groundwater information right now. Please try again.',
      err?.code ?? 'http_error', res.status, err?.missing ?? [],
    )
  }
  return body as T
}

function cached<T>(key: string, load: () => Promise<T>, ttl = TTL_MS): Promise<T> {
  const hit = cache.get(key)
  if (hit && Date.now() - hit.at < ttl) return Promise.resolve(hit.value as T)
  const running = inflight.get(key)
  if (running) return running as Promise<T>
  const p = load()
    .then((value) => {
      cache.set(key, { at: Date.now(), value })
      return value
    })
    .finally(() => inflight.delete(key))
  inflight.set(key, p)
  return p
}

const qs = (p: LatLng, radius: number, extra: Record<string, string | number> = {}) =>
  new URLSearchParams({
    latitude: String(p.latitude), longitude: String(p.longitude), radius_km: String(radius),
    ...Object.fromEntries(Object.entries(extra).map(([k, v]) => [k, String(v)])),
  }).toString()

export const api = {
  health: () => send<Health>('/api/health'),

  nearbyWells: (p: LatLng, radius: number, limit = 500) => {
    const path = `/api/wells/nearby?${qs(p, radius, { limit })}`
    return cached(path, () => send<NearbyResponse>(path))
  },
  summary: (p: LatLng, radius: number) => {
    const path = `/api/groundwater/summary?${qs(p, radius)}`
    return cached(path, () => send<SummaryResponse>(path))
  },
  wellDetails: (id: string) => {
    const path = `/api/wells/${encodeURIComponent(id)}`
    return cached(path, () => send<WellDetails>(path))
  },
  waterQuality: (p: LatLng, radius: number) => {
    const path = `/api/water-quality?${qs(p, radius)}`
    return cached(path, () => send<QualityResponse>(path))
  },
  compare: (a: LatLng, b: LatLng, radius: number) => {
    const body = JSON.stringify({ property_a: a, property_b: b, radius_km: radius })
    return cached(`POST /api/properties/compare ${body}`, () =>
      send<CompareResponse>('/api/properties/compare', { method: 'POST', body }))
  },
  geocode: (q: string) => send<{ results: GeocodeResult[] }>(`/api/geocode?${new URLSearchParams({ q })}`),

  // chat is never cached: every question is a fresh conversation turn
  genieChat: (message: string, conversationId: string | null, context?: LatLng & { radius_km: number }) =>
    send<GenieChatResponse>('/api/genie/chat', {
      method: 'POST',
      body: JSON.stringify({ message, conversation_id: conversationId, context: context ?? null }),
    }),
}
