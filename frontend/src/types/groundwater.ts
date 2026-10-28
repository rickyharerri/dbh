// Mirrors backend/models.py. Optional values are `null` when the source has no value — never 0.

export type TabId = 'explore' | 'quality' | 'compare' | 'ask'
export const RADII = [1, 2, 5, 10, 20] as const
export type Radius = (typeof RADII)[number]
export const DEFAULT_RADIUS: Radius = 5

export interface LatLng { latitude: number; longitude: number }

export interface Units { depth: string | null; well_yield: string | null; static_water_level: string | null }

export interface Capabilities {
  depth: boolean
  well_yield: boolean
  static_water_level: boolean
  drilling_date: boolean
  status: boolean
  quality: boolean
  units: Units
  low_yield_threshold: number | null
  source_dataset: string | null
}

export type DataSource = 'databricks' | 'demo'

export interface Health {
  status: string
  mode: 'live' | 'demo' | 'unconfigured'
  features: {
    depth: boolean; well_yield: boolean; static_water_level: boolean; drilling_date: boolean
    status: boolean; quality: boolean; low_yield_threshold: number | null
    genie: boolean; geocoding: boolean
  }
  units: Units
  source_dataset: string | null
  warnings: string[]
  min_sample_size: number
  missing_configuration?: string[]
}

export interface Well {
  well_id: string
  latitude: number
  longitude: number
  distance_km: number
  depth: number | null
  well_yield: number | null
  static_water_level: number | null
  drilling_date: string | null
  status: string | null
}

export interface NearbyResponse {
  location: LatLng
  radius_km: number
  total_wells: number
  returned_wells: number
  limit: number
  truncated: boolean
  units: Units
  capabilities: Capabilities
  wells: Well[]
  data_source: DataSource
  disclaimer: string
}

export type QualityStatus = 'no_data' | 'not_evaluated' | 'within_guideline' | 'above_guideline'

export interface QualityMeasurement {
  well_id: string
  distance_km: number | null
  parameter: string
  value: number | null
  value_raw: string | null
  unit: string | null
  sample_date: string | null
  guideline_value: number | null
  guideline_unit: string | null
  guideline_reference: string | null
  status: QualityStatus
}

export interface WellDetails {
  well_id: string
  latitude: number
  longitude: number
  depth: number | null
  well_yield: number | null
  static_water_level: number | null
  drilling_date: string | null
  status: string | null
  units: Units
  capabilities: Capabilities
  quality: QualityMeasurement[]
  source_dataset: string | null
  data_source: DataSource
  disclaimer: string
}

export interface Metric { available: boolean; median: number | null; sample_count: number; unit: string | null }
export interface HistogramBin { label: string; start: number; end: number | null; count: number }
export interface Histogram { unit: string | null; sample_count: number; bins: HistogramBin[] }

export interface SummaryResponse {
  location: LatLng
  radius_km: number
  total_wells: number
  depth: Metric
  well_yield: Metric
  static_water_level: Metric
  quality: { available: boolean; wells_with_quality: number; observation_count: number }
  low_yield: { threshold: number; unit: string | null; count: number; sample_count: number } | null
  latest_record_date: string | null
  histograms: { depth: Histogram; well_yield: Histogram }
  limited_data: boolean
  notes: string[]
  data_source: DataSource
  disclaimer: string
}

export interface QualityResponse {
  location: LatLng
  radius_km: number
  available: boolean
  total_records: number
  returned_records: number
  parameters: { parameter: string; observations: number; wells: number; latest_sample_date: string | null }[]
  measurements: QualityMeasurement[]
  guideline: { configured: boolean; reference: string | null; version: string | null }
  explanation: string | null
  data_source: DataSource
  disclaimer: string
}

export interface CompareRow {
  key: string
  label: string
  a: number | string | null
  b: number | string | null
  unit: string | null
  a_samples: number | null
  b_samples: number | null
  available: boolean
}

export interface CompareResponse {
  radius_km: number
  property_a: SummaryResponse
  property_b: SummaryResponse
  rows: CompareRow[]
  summary_text: string
  data_source: DataSource
  disclaimer: string
}

export interface GenieTable { columns: string[]; rows: (string | null)[][]; row_count: number; truncated: boolean }
export interface GenieChatResponse {
  conversation_id: string | null
  message_id: string | null
  status: 'completed' | 'failed' | 'timeout' | 'cancelled'
  answer: string | null
  query: { description: string | null; sql: string | null } | null
  data: GenieTable | null
  error: string | null
}

export interface GeocodeResult { name: string; latitude: number; longitude: number }
