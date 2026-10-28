/* App-wide state with React's own useReducer + context (no external state library).
 * State is lifted here so the selected location, results and chat survive tab changes. */
import {
  createContext, useCallback, useContext, useEffect, useMemo, useReducer, useRef, type ReactNode,
} from 'react'
import { api, ApiError } from '../services/api'
import {
  DEFAULT_RADIUS, type CompareResponse, type GenieChatResponse, type Health, type LatLng, type NearbyResponse,
  type QualityResponse, type Radius, type SummaryResponse, type TabId,
} from '../types/groundwater'

export type Async<T> =
  | { status: 'idle' }
  | { status: 'loading'; key: string }
  | { status: 'success'; key: string; data: T }
  | { status: 'error'; key: string; message: string; code: string; missing: string[] }

const idle = { status: 'idle' } as const
export const searchKey = (p: LatLng, r: number) => `${p.latitude},${p.longitude},${r}`

export interface Analysis { nearby: NearbyResponse; summary: SummaryResponse }

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant' | 'error'
  text: string
  response?: GenieChatResponse
}

export interface State {
  tab: TabId
  health: Async<Health>
  location: LatLng | null
  /** bumped when the location is set by typing/search so the map re-centres (not on map clicks) */
  focusNonce: number
  radiusKm: Radius
  analysis: Async<Analysis>
  quality: Async<QualityResponse>
  selectedWellId: string | null
  selectNonce: number
  detailsWellId: string | null
  compare: { a: LatLng | null; b: LatLng | null; radiusKm: Radius; picking: 'a' | 'b'; focusNonce: number; result: Async<CompareResponse> }
  chat: { messages: ChatMessage[]; conversationId: string | null; sending: boolean; includeLocation: boolean }
}

export const initialState: State = {
  tab: 'explore',
  health: idle,
  location: null,
  focusNonce: 0,
  radiusKm: DEFAULT_RADIUS,
  analysis: idle,
  quality: idle,
  selectedWellId: null,
  selectNonce: 0,
  detailsWellId: null,
  compare: { a: null, b: null, radiusKm: DEFAULT_RADIUS, picking: 'a', focusNonce: 0, result: idle },
  chat: { messages: [], conversationId: null, sending: false, includeLocation: false },
}

type Action =
  | { type: 'tab'; tab: TabId }
  | { type: 'health'; value: Async<Health> }
  | { type: 'location'; location: LatLng; recentre: boolean }
  | { type: 'radius'; radiusKm: Radius }
  | { type: 'analysis'; value: Async<Analysis> }
  | { type: 'quality'; value: Async<QualityResponse> }
  | { type: 'selectWell'; id: string | null }
  | { type: 'openDetails'; id: string | null }
  | { type: 'compareLocation'; which: 'a' | 'b'; location: LatLng; recentre: boolean }
  | { type: 'comparePicking'; which: 'a' | 'b' }
  | { type: 'compareRadius'; radiusKm: Radius }
  | { type: 'compareResult'; value: Async<CompareResponse> }
  | { type: 'chatSending'; message: ChatMessage }
  | { type: 'chatReply'; message: ChatMessage; conversationId: string | null }
  | { type: 'chatClear' }
  | { type: 'chatIncludeLocation'; value: boolean }

export function reducer(s: State, a: Action): State {
  switch (a.type) {
    case 'tab': return { ...s, tab: a.tab }
    case 'health': return { ...s, health: a.value }
    case 'location':
      return { ...s, location: a.location, focusNonce: s.focusNonce + (a.recentre ? 1 : 0), selectedWellId: null }
    case 'radius': return { ...s, radiusKm: a.radiusKm }
    case 'analysis': return { ...s, analysis: a.value, selectedWellId: null, focusNonce: a.value.status === 'success' ? s.focusNonce + 1 : s.focusNonce }
    case 'quality': return { ...s, quality: a.value }
    case 'selectWell': return { ...s, selectedWellId: a.id, selectNonce: s.selectNonce + 1 }
    case 'openDetails': return { ...s, detailsWellId: a.id }
    case 'compareLocation':
      return { ...s, compare: { ...s.compare, [a.which]: a.location, focusNonce: s.compare.focusNonce + (a.recentre ? 1 : 0) } }
    case 'comparePicking': return { ...s, compare: { ...s.compare, picking: a.which } }
    case 'compareRadius': return { ...s, compare: { ...s.compare, radiusKm: a.radiusKm } }
    case 'compareResult':
      return { ...s, compare: { ...s.compare, result: a.value, focusNonce: s.compare.focusNonce + (a.value.status === 'success' ? 1 : 0) } }
    case 'chatSending':
      return { ...s, chat: { ...s.chat, sending: true, messages: [...s.chat.messages, a.message] } }
    case 'chatReply':
      return {
        ...s,
        chat: { ...s.chat, sending: false, conversationId: a.conversationId ?? s.chat.conversationId, messages: [...s.chat.messages, a.message] },
      }
    case 'chatClear': return { ...s, chat: { ...s.chat, messages: [], conversationId: null, sending: false } }
    case 'chatIncludeLocation': return { ...s, chat: { ...s.chat, includeLocation: a.value } }
  }
}

const toError = (key: string, e: unknown): Async<never> => {
  const err = e instanceof ApiError ? e : null
  return {
    status: 'error', key, code: err?.code ?? 'unknown', missing: err?.missing ?? [],
    message: err?.message ?? 'We couldn’t retrieve groundwater information right now. Please try again.',
  }
}

export interface Actions {
  setTab(tab: TabId): void
  setLocation(p: LatLng, opts?: { recentre?: boolean }): void
  setRadius(r: Radius): void
  analyze(): Promise<void>
  loadQuality(): Promise<void>
  selectWell(id: string | null): void
  openDetails(id: string | null): void
  setCompareLocation(which: 'a' | 'b', p: LatLng, opts?: { recentre?: boolean }): void
  setComparePicking(which: 'a' | 'b'): void
  setCompareRadius(r: Radius): void
  runCompare(): Promise<void>
  sendChat(text: string): Promise<void>
  clearChat(): void
  setIncludeLocation(v: boolean): void
}

const StateCtx = createContext<State | null>(null)
const ActionsCtx = createContext<Actions | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  const ref = useRef(state)
  ref.current = state
  // Only the newest request of each kind may write results (older, slower ones are ignored).
  const seq = useRef({ analysis: 0, quality: 0, compare: 0 })
  const msgId = useRef(0)

  const actions = useMemo<Actions>(() => ({
    setTab: (tab) => dispatch({ type: 'tab', tab }),
    setLocation: (location, opts) => dispatch({ type: 'location', location, recentre: opts?.recentre ?? false }),
    setRadius: (radiusKm) => dispatch({ type: 'radius', radiusKm }),

    async analyze() {
      const { location, radiusKm } = ref.current
      if (!location) return
      const key = searchKey(location, radiusKm)
      const id = ++seq.current.analysis
      void import('../components/HistogramChart') // warm the charts chunk while the query runs
      dispatch({ type: 'analysis', value: { status: 'loading', key } })
      try {
        // nearby wells and the summary are independent queries: run them in parallel
        const [nearby, summary] = await Promise.all([api.nearbyWells(location, radiusKm), api.summary(location, radiusKm)])
        if (id === seq.current.analysis) dispatch({ type: 'analysis', value: { status: 'success', key, data: { nearby, summary } } })
      } catch (e) {
        if (id === seq.current.analysis) dispatch({ type: 'analysis', value: toError(key, e) })
      }
    },

    async loadQuality() {
      // quality is fetched for the location/radius that was analysed, and only when that tab is opened
      const a = ref.current.analysis
      if (a.status !== 'success') return
      const { location, radius_km } = a.data.nearby
      const key = searchKey(location, radius_km)
      const q = ref.current.quality
      if ((q.status === 'success' || q.status === 'loading') && q.key === key) return
      const id = ++seq.current.quality
      dispatch({ type: 'quality', value: { status: 'loading', key } })
      try {
        const data = await api.waterQuality(location, radius_km)
        if (id === seq.current.quality) dispatch({ type: 'quality', value: { status: 'success', key, data } })
      } catch (e) {
        if (id === seq.current.quality) dispatch({ type: 'quality', value: toError(key, e) })
      }
    },

    selectWell: (id) => dispatch({ type: 'selectWell', id }),
    openDetails: (id) => dispatch({ type: 'openDetails', id }),

    setCompareLocation: (which, location, opts) =>
      dispatch({ type: 'compareLocation', which, location, recentre: opts?.recentre ?? false }),
    setComparePicking: (which) => dispatch({ type: 'comparePicking', which }),
    setCompareRadius: (radiusKm) => dispatch({ type: 'compareRadius', radiusKm }),

    async runCompare() {
      const { a, b, radiusKm } = ref.current.compare
      if (!a || !b) return
      const key = `${searchKey(a, radiusKm)}|${searchKey(b, radiusKm)}`
      const id = ++seq.current.compare
      dispatch({ type: 'compareResult', value: { status: 'loading', key } })
      try {
        const data = await api.compare(a, b, radiusKm)
        if (id === seq.current.compare) dispatch({ type: 'compareResult', value: { status: 'success', key, data } })
      } catch (e) {
        if (id === seq.current.compare) dispatch({ type: 'compareResult', value: toError(key, e) })
      }
    },

    async sendChat(text) {
      const { chat, location, radiusKm } = ref.current
      const message = text.trim()
      if (!message || chat.sending) return
      dispatch({ type: 'chatSending', message: { id: ++msgId.current, role: 'user', text: message } })
      const context = chat.includeLocation && location ? { ...location, radius_km: radiusKm } : undefined
      try {
        const res = await api.genieChat(message, chat.conversationId, context)
        const ok = res.status === 'completed'
        dispatch({
          type: 'chatReply', conversationId: res.conversation_id,
          message: {
            id: ++msgId.current, role: ok ? 'assistant' : 'error',
            text: ok ? (res.answer ?? '') : (res.error ?? 'The AI assistant couldn’t complete your question. Please try rephrasing it.'),
            response: res,
          },
        })
      } catch (e) {
        dispatch({
          type: 'chatReply', conversationId: null,
          message: {
            id: ++msgId.current, role: 'error',
            text: e instanceof ApiError ? e.message : 'The AI assistant couldn’t complete your question. Please try rephrasing it.',
          },
        })
      }
    },
    clearChat: () => dispatch({ type: 'chatClear' }),
    setIncludeLocation: (value) => dispatch({ type: 'chatIncludeLocation', value }),
  }), [])

  // fetch capabilities once at start-up (fast endpoint, no warehouse query)
  useEffect(() => {
    let live = true
    dispatch({ type: 'health', value: { status: 'loading', key: 'health' } })
    api.health()
      .then((data) => live && dispatch({ type: 'health', value: { status: 'success', key: 'health', data } }))
      .catch((e) => live && dispatch({ type: 'health', value: toError('health', e) }))
    return () => { live = false }
  }, [])

  return (
    <ActionsCtx.Provider value={actions}>
      <StateCtx.Provider value={state}>{children}</StateCtx.Provider>
    </ActionsCtx.Provider>
  )
}

export function useAppState(): State {
  const s = useContext(StateCtx)
  if (!s) throw new Error('useAppState must be used inside AppProvider')
  return s
}
export function useActions(): Actions {
  const a = useContext(ActionsCtx)
  if (!a) throw new Error('useActions must be used inside AppProvider')
  return a
}

export const useHealth = (): Health | null => {
  const { health } = useAppState()
  return health.status === 'success' ? health.data : null
}

/** Stable callback used by pages that only need to open a tab. */
export function useGoTo() {
  const { setTab } = useActions()
  return useCallback((tab: TabId) => setTab(tab), [setTab])
}
