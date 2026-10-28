import type { Capabilities, CompareResponse, Health, NearbyResponse, SummaryResponse } from '../types/groundwater'

export const caps: Capabilities = {
  depth: true, well_yield: true, static_water_level: false, drilling_date: true, status: true, quality: true,
  units: { depth: 'm', well_yield: 'gpm', static_water_level: null }, low_yield_threshold: 3, source_dataset: 'test.dataset.wells',
}

export const health = (over: Partial<Health['features']> = {}, mode: Health['mode'] = 'live'): Health => ({
  status: 'healthy', mode, features: { ...caps, genie: true, geocoding: false, ...over }, units: caps.units,
  source_dataset: caps.source_dataset, warnings: [], min_sample_size: 5,
})

export const summary = (radius = 5, over: Partial<SummaryResponse> = {}): SummaryResponse => ({
  location: { latitude: 51.19, longitude: -114.47 }, radius_km: radius, total_wells: 86,
  depth: { available: true, median: 75, sample_count: 81, unit: 'm' },
  well_yield: { available: true, median: 8.5, sample_count: 74, unit: 'gpm' },
  static_water_level: { available: false, median: null, sample_count: 0, unit: null },
  quality: { available: true, wells_with_quality: 9, observation_count: 22 },
  low_yield: { threshold: 3, unit: 'gpm', count: 9, sample_count: 74 },
  latest_record_date: '2023-11-02',
  histograms: {
    depth: { unit: 'm', sample_count: 81, bins: [{ label: '0–25', start: 0, end: 25, count: 11 }, { label: '25–50', start: 25, end: 50, count: 70 }] },
    well_yield: { unit: 'gpm', sample_count: 74, bins: [{ label: '0–5', start: 0, end: 5, count: 74 }] },
  },
  limited_data: false, notes: [], data_source: 'databricks', disclaimer: 'Historical records — not a water safety certification.', ...over,
})

export const nearby = (radius = 5): NearbyResponse => ({
  location: { latitude: 51.19, longitude: -114.47 }, radius_km: radius, total_wells: 86, returned_wells: 2, limit: 500, truncated: true,
  units: caps.units, capabilities: caps, data_source: 'databricks', disclaimer: 'Historical records — not a water safety certification.',
  wells: [
    { well_id: 'W-001', latitude: 51.19, longitude: -114.47, distance_km: 0.3, depth: 82, well_yield: 12, static_water_level: null, drilling_date: '2020-01-02', status: 'Active' },
    { well_id: 'W-002', latitude: 51.2, longitude: -114.48, distance_km: 0.9, depth: null, well_yield: null, static_water_level: null, drilling_date: null, status: null },
  ],
})

export const compare = (): CompareResponse => ({
  radius_km: 5, property_a: summary(5), property_b: summary(5, { total_wells: 40 }),
  rows: [
    { key: 'total_wells', label: 'Nearby wells', a: 86, b: 40, unit: null, a_samples: null, b_samples: null, available: true },
    { key: 'depth', label: 'Typical well depth (median)', a: 75, b: 60, unit: 'm', a_samples: 81, b_samples: 38, available: true },
  ],
  summary_text: 'Within 5 km, Property A has 86 historical wells on record and Property B has 40. These figures do not guarantee anything. Test your own water.',
  data_source: 'databricks', disclaimer: 'Historical records — not a water safety certification.',
})
