import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import App from '../App'
import { AppProvider } from '../state/AppContext'
import * as fx from './fixtures'

// Leaflet needs real layout; replace the map with a stub that behaves like a user clicking it.
const picks = vi.hoisted(() => ({ n: 0 }))
vi.mock('../components/WellMap', () => ({
  default: (props: { onPick: (p: { latitude: number; longitude: number }) => void; wells?: unknown[]; points: unknown[]; radiusKm: number }) => (
    <div data-testid="map">
      <button type="button" onClick={() => props.onPick({ latitude: 51.19 + picks.n++ * 0.5, longitude: -114.47 })}>Mock map click</button>
      <span>{props.wells?.length ?? 0} well markers, {props.points.length} points, radius {props.radiusKm}</span>
    </div>
  ),
}))

type Handler = (url: URL, init?: RequestInit) => { status?: number; body: unknown } | Promise<{ status?: number; body: unknown }>

function mockApi(handlers: Record<string, Handler> = {}, healthBody = fx.health()) {
  const calls: { url: URL; init?: RequestInit }[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost')
    calls.push({ url, init })
    const defaults: Record<string, Handler> = {
      '/api/health': () => ({ body: healthBody }),
      '/api/wells/nearby': (u) => ({ body: fx.nearby(Number(u.searchParams.get('radius_km'))) }),
      '/api/groundwater/summary': (u) => ({ body: fx.summary(Number(u.searchParams.get('radius_km'))) }),
      '/api/properties/compare': () => ({ body: fx.compare() }),
    }
    const h = handlers[url.pathname] ?? defaults[url.pathname]
    if (!h) return new Response(JSON.stringify({ error: { code: 'not_found', message: 'Unknown API endpoint.' } }), { status: 404 })
    const { status = 200, body } = await h(url, init)
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fetchMock)
  return { calls, fetchMock }
}

const comparePanel = () => screen.getByRole('tabpanel', { name: 'Compare Properties' })
const renderApp = () => render(<AppProvider><App /></AppProvider>)
const user = () => userEvent.setup()

beforeEach(() => { picks.n = 0 })
afterEach(() => vi.unstubAllGlobals())

describe('navigation', () => {
  it('shows the header, tagline and the four sections, and switches between them', async () => {
    mockApi()
    const u = user()
    renderApp()
    expect(screen.getByText('AquaWise Alberta')).toBeInTheDocument()
    expect(screen.getByText('Understand the water beneath your property.')).toBeInTheDocument()
    const tabs = screen.getAllByRole('tab').map((t) => t.textContent)
    expect(tabs).toEqual(['Explore Property', 'Water Quality', 'Compare Properties', 'Ask AquaWise'])

    expect(await screen.findByRole('heading', { name: /Explore groundwater near your property/i })).toBeInTheDocument()
    await u.click(screen.getByRole('tab', { name: 'Water Quality' }))
    expect(await screen.findByRole('heading', { name: 'Historical water quality' })).toBeInTheDocument()
    await u.click(screen.getByRole('tab', { name: 'Compare Properties' }))
    expect(await screen.findByRole('heading', { name: 'Compare two properties' })).toBeInTheDocument()
    await u.click(screen.getByRole('tab', { name: 'Ask AquaWise' }))
    expect(await screen.findByRole('heading', { name: 'Ask AquaWise' })).toBeInTheDocument()
  })

  it('opens the About dialog', async () => {
    mockApi()
    const u = user()
    renderApp()
    await u.click(screen.getByRole('button', { name: 'About' }))
    const dialog = screen.getByRole('dialog', { name: /About AquaWise/ })
    expect(within(dialog).getByText(/not a water safety/i)).toBeInTheDocument()
  })
})

describe('Explore Property', () => {
  it('selects a location on the map, changes radius, analyzes and renders API results', async () => {
    const { calls } = mockApi()
    const u = user()
    renderApp()
    await screen.findByTestId('map')
    expect(screen.getByRole('button', { name: 'Analyze Groundwater' })).toBeDisabled()

    await u.click(screen.getByRole('button', { name: 'Mock map click' }))
    expect(screen.getByText('51.19000, -114.47000')).toBeInTheDocument() // selected coordinates are displayed
    expect(screen.getByLabelText('Latitude')).toHaveValue('51.19')

    expect(screen.getByRole('radio', { name: '5 km' })).toBeChecked() // default radius
    await u.click(screen.getByRole('radio', { name: '10 km' }))

    await u.click(screen.getByRole('button', { name: 'Analyze Groundwater' }))
    expect(await screen.findByText(/Within 10 km: 86 historical wells/)).toBeInTheDocument()

    const nearbyCall = calls.find((c) => c.url.pathname === '/api/wells/nearby')!
    expect(nearbyCall.url.searchParams.get('radius_km')).toBe('10')
    expect(nearbyCall.url.searchParams.get('latitude')).toBe('51.19')

    // four cards with real numbers, units and sample sizes
    expect(screen.getByText('75 metres')).toBeInTheDocument()
    expect(screen.getByText(/Median of 81 of 86 wells with a recorded depth/)).toBeInTheDocument()
    expect(screen.getByText('8.5 gallons per minute')).toBeInTheDocument()
    expect(screen.getByText(/22 observations in total/)).toBeInTheDocument()
    expect(screen.getByText(/showing|nearest 2 wells/i)).toBeInTheDocument()
    // markers reach the map; table shows missing values as "Not available" (never 0)
    expect(screen.getByText(/2 well markers/)).toBeInTheDocument()
    const row = screen.getByRole('row', { name: /W-002/ })
    expect(within(row).getAllByText('Not available').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText(/not a water safety certification/i).length).toBeGreaterThan(0)
  })

  it('shows "Not available" instead of zero when a measurement has no data', async () => {
    mockApi({
      '/api/groundwater/summary': () => ({
        body: fx.summary(5, { well_yield: { available: true, median: null, sample_count: 0, unit: 'gpm' },
          histograms: { depth: fx.summary().histograms.depth, well_yield: { unit: 'gpm', sample_count: 0, bins: [] } } }),
      }),
    })
    const u = user()
    renderApp()
    await u.click(await screen.findByRole('button', { name: 'Mock map click' }))
    await u.click(screen.getByRole('button', { name: 'Analyze Groundwater' }))
    const card = await screen.findByRole('region', { name: 'Typical well yield' })
    expect(within(card).getByText('Not available')).toBeInTheDocument()
    expect(card).not.toHaveTextContent(/\b0 gallons/)
    expect((await screen.findAllByText(/No yield was recorded/)).length).toBeGreaterThan(0) // card + chart both explain
  })

  it('rejects invalid coordinates without calling the API', async () => {
    const { calls } = mockApi()
    const u = user()
    renderApp()
    await screen.findByTestId('map')
    await u.type(screen.getByLabelText('Latitude'), '95')
    await u.type(screen.getByLabelText('Longitude'), '-114.4')
    await u.click(screen.getByRole('button', { name: 'Set location' }))
    expect(await screen.findByText('Latitude must be between -90 and 90.')).toHaveAttribute('role', 'alert')
    expect(screen.getByRole('button', { name: 'Analyze Groundwater' })).toBeDisabled()
    expect(calls.some((c) => c.url.pathname.startsWith('/api/wells'))).toBe(false)
  })

  it('accepts typed coordinates', async () => {
    mockApi()
    const u = user()
    renderApp()
    await screen.findByTestId('map')
    await u.type(screen.getByLabelText('Latitude'), '51.19')
    await u.type(screen.getByLabelText('Longitude'), '-114.47')
    await u.click(screen.getByRole('button', { name: 'Set location' }))
    expect(screen.getByRole('button', { name: 'Analyze Groundwater' })).toBeEnabled()
  })

  it('shows a loading state, then a friendly error with retry when Databricks is unavailable', async () => {
    let release!: () => void
    const gate = new Promise<void>((r) => { release = r })
    mockApi({
      '/api/wells/nearby': async () => { await gate; return { status: 502, body: { error: { code: 'data_unavailable', message: 'We couldn’t retrieve groundwater information right now. Please try again.' } } } },
    })
    const u = user()
    renderApp()
    await u.click(await screen.findByRole('button', { name: 'Mock map click' }))
    await u.click(screen.getByRole('button', { name: 'Analyze Groundwater' }))
    expect(await screen.findByText('Searching nearby wells…')).toBeInTheDocument()
    await act(async () => release())
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('We couldn’t retrieve groundwater information right now')
    expect(within(alert).getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it('explains an empty result', async () => {
    mockApi({ '/api/wells/nearby': () => ({ body: { ...fx.nearby(), total_wells: 0, returned_wells: 0, wells: [], truncated: false } }) })
    const u = user()
    renderApp()
    await u.click(await screen.findByRole('button', { name: 'Mock map click' }))
    await u.click(screen.getByRole('button', { name: 'Analyze Groundwater' }))
    expect(await screen.findByText(/No historical wells were found within the selected radius/)).toBeInTheDocument()
  })

  it('reports missing server configuration without exposing anything secret', async () => {
    mockApi({}, { ...fx.health(), mode: 'unconfigured', missing_configuration: ['DATABRICKS_HOST', 'WELLS_TABLE'] })
    renderApp()
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Groundwater data isn’t connected yet')
    expect(alert).toHaveTextContent('DATABRICKS_HOST, WELLS_TABLE')
  })

  it('shows a persistent demo banner in demo mode', async () => {
    mockApi({}, fx.health({}, 'demo'))
    renderApp()
    expect(await screen.findByText(/synthetic and randomly generated/)).toBeInTheDocument()
  })
})

describe('Compare Properties', () => {
  it('selects two properties independently and renders a side-by-side comparison', async () => {
    const { calls } = mockApi()
    const u = user()
    renderApp()
    await u.click(await screen.findByRole('tab', { name: 'Compare Properties' }))
    await screen.findByRole('heading', { name: 'Compare two properties' })
    const compareBtn = within(comparePanel()).getByRole('button', { name: 'Compare Properties' })
    expect(compareBtn).toBeDisabled()

    await u.click(await screen.findByRole('button', { name: 'Mock map click' })) // -> Property A
    await u.click(screen.getByRole('button', { name: 'Mock map click' })) // flow moves on to Property B
    const [latA, latB] = within(comparePanel()).getAllByLabelText('Latitude')
    expect(latA).toHaveValue('51.19')
    expect(latB).toHaveValue('51.69') // second click went to Property B
    await u.click(screen.getByRole('radio', { name: '20 km' }))
    expect(compareBtn).toBeEnabled()
    await u.click(compareBtn)

    const table = await screen.findByRole('table', { name: /Side-by-side comparison/ })
    expect(within(table).getByText('Nearby wells')).toBeInTheDocument()
    expect(within(table).getByText('86')).toBeInTheDocument()
    expect(screen.getByText(/Property A has 86 historical wells/)).toBeInTheDocument()
    const post = calls.find((c) => c.url.pathname === '/api/properties/compare')!
    const body = JSON.parse(String(post.init?.body))
    expect(body.radius_km).toBe(20)
    expect(body.property_a.latitude).not.toBe(body.property_b.latitude) // independent selections
  })

  it('shows an error if the comparison fails', async () => {
    mockApi({ '/api/properties/compare': () => ({ status: 502, body: { error: { code: 'data_unavailable', message: 'We couldn’t retrieve groundwater information right now. Please try again.' } } }) })
    const u = user()
    renderApp()
    await u.click(await screen.findByRole('tab', { name: 'Compare Properties' }))
    await u.click(await screen.findByRole('button', { name: 'Mock map click' }))
    await u.click(screen.getByRole('button', { name: 'Mock map click' }))
    await u.click(within(comparePanel()).getByRole('button', { name: 'Compare Properties' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/couldn’t retrieve groundwater/)
  })
})

describe('Ask AquaWise', () => {
  const genieReply = {
    conversation_id: 'conv-1', message_id: 'm1', status: 'completed', error: null,
    answer: 'There are 42 wells near Cochrane.',
    query: { description: 'Count wells', sql: 'SELECT COUNT(*) AS wells FROM wells' },
    data: { columns: ['wells'], rows: [['42']], row_count: 1, truncated: false },
  }

  it('sends a suggested question, shows loading, then the answer, table and query; follow-ups keep the conversation id', async () => {
    let release!: () => void
    const gate = new Promise<void>((r) => { release = r })
    const bodies: Record<string, unknown>[] = []
    mockApi({
      '/api/genie/chat': async (_u, init) => {
        bodies.push(JSON.parse(String(init?.body)))
        if (bodies.length === 1) await gate
        return { body: genieReply }
      },
    })
    const u = user()
    renderApp()
    await u.click(await screen.findByRole('tab', { name: 'Ask AquaWise' }))
    await u.click(await screen.findByRole('button', { name: 'How many water wells are near Cochrane?' }))

    expect(await screen.findByText(/working on your question/)).toBeInTheDocument()
    expect(screen.getByText('How many water wells are near Cochrane?', { selector: 'p' })).toBeInTheDocument()
    await act(async () => release())
    expect(await screen.findByText('There are 42 wells near Cochrane.')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Query result table' })).toHaveTextContent('42')
    expect(screen.getByText('SELECT COUNT(*) AS wells FROM wells')).toBeInTheDocument()
    expect(bodies[0]).toMatchObject({ conversation_id: null, context: null }) // location NOT sent unless the user opts in

    await u.type(screen.getByLabelText('Your question'), 'And the deepest?')
    await u.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(bodies).toHaveLength(2))
    expect(bodies[1]).toMatchObject({ conversation_id: 'conv-1', message: 'And the deepest?' })
  })

  it('only sends the map location when the user opts in', async () => {
    const bodies: Record<string, unknown>[] = []
    mockApi({ '/api/genie/chat': (_u, init) => { bodies.push(JSON.parse(String(init?.body))); return { body: genieReply } } })
    const u = user()
    renderApp()
    await u.click(await screen.findByRole('button', { name: 'Mock map click' }))
    await u.click(screen.getByRole('tab', { name: 'Ask AquaWise' }))
    const box = await screen.findByRole('checkbox', { name: /Include my selected map location/ })
    await u.click(box)
    await u.type(screen.getByLabelText('Your question'), 'Typical depth?')
    await u.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(bodies).toHaveLength(1))
    expect(bodies[0].context).toEqual({ latitude: 51.19, longitude: -114.47, radius_km: 5 })
  })

  it('shows a clear error when the assistant fails, and can clear the conversation', async () => {
    mockApi({ '/api/genie/chat': () => ({ body: { ...genieReply, status: 'failed', answer: null, query: null, data: null, error: 'The AI assistant couldn’t complete your question. Please try rephrasing it.' } }) })
    const u = user()
    renderApp()
    await u.click(await screen.findByRole('tab', { name: 'Ask AquaWise' }))
    await u.type(await screen.findByLabelText('Your question'), 'hello')
    await u.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('couldn’t complete your question')
    await u.click(screen.getByRole('button', { name: 'Clear conversation' }))
    expect(screen.getByText(/No messages yet/)).toBeInTheDocument()
  })

  it('shows "AI assistant not configured" and blocks input instead of faking answers', async () => {
    const { calls } = mockApi({}, fx.health({ genie: false }))
    const u = user()
    renderApp()
    await u.click(await screen.findByRole('tab', { name: 'Ask AquaWise' }))
    expect(await screen.findByText('AI assistant not configured')).toBeInTheDocument()
    expect(screen.getByLabelText('Your question')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'How many water wells are near Cochrane?' })).toBeDisabled()
    expect(calls.some((c) => c.url.pathname === '/api/genie/chat')).toBe(false)
  })
})

describe('Water Quality', () => {
  it('asks for a location first, then lists observed measurements with statuses and the disclaimer', async () => {
    const q = {
      location: { latitude: 51.19, longitude: -114.47 }, radius_km: 5, available: true, total_records: 2, returned_records: 2,
      parameters: [{ parameter: 'Nitrate', observations: 1, wells: 1, latest_sample_date: '2019-06-15' }, { parameter: 'Arsenic', observations: 1, wells: 1, latest_sample_date: '2018-01-01' }],
      measurements: [
        { well_id: 'W-001', distance_km: 0.3, parameter: 'Nitrate', value: 12, value_raw: '12', unit: 'mg/L', sample_date: '2019-06-15', guideline_value: 10, guideline_unit: 'mg/L', guideline_reference: 'Test ref v1', status: 'above_guideline' },
        { well_id: 'W-002', distance_km: 0.9, parameter: 'Arsenic', value: null, value_raw: '<0.001', unit: 'mg/L', sample_date: '2018-01-01', guideline_value: null, guideline_unit: null, guideline_reference: null, status: 'no_data' },
      ],
      guideline: { configured: true, reference: 'Test ref', version: 'v1' }, explanation: null, data_source: 'databricks', disclaimer: '',
    }
    mockApi({ '/api/water-quality': () => ({ body: q }) })
    const u = user()
    renderApp()
    await u.click(await screen.findByRole('tab', { name: 'Water Quality' }))
    expect(await screen.findByText('Choose a location first')).toBeInTheDocument()

    await u.click(screen.getByRole('tab', { name: 'Explore Property' }))
    await u.click(await screen.findByRole('button', { name: 'Mock map click' }))
    await u.click(screen.getByRole('button', { name: 'Analyze Groundwater' }))
    await screen.findByText(/Within 5 km/)
    await u.click(screen.getByRole('tab', { name: 'Water Quality' }))

    expect(await screen.findByText('2 measurements found')).toBeInTheDocument()
    expect(screen.getByText('Above guideline')).toBeInTheDocument()
    expect(screen.getByText('No data')).toBeInTheDocument()
    expect(screen.getByText(/<0.001 mg\/L \(as recorded\)/)).toBeInTheDocument()
    expect(screen.getAllByText(/do not establish whether water at this property is safe to drink/i).length).toBeGreaterThan(0)
    // filtering by parameter
    await u.click(screen.getByRole('button', { name: /Nitrate/ }))
    expect(screen.queryByText('Arsenic', { selector: 'th' })).not.toBeInTheDocument()
  })
})
