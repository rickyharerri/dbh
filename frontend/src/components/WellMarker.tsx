import { memo } from 'react'
import { CircleMarker } from 'react-leaflet'
import type { Well } from '../types/groundwater'

/** One historical well. Memoised + drawn on a canvas, so hundreds of points stay smooth. */
const WellMarker = memo(function WellMarker({ well, selected, onSelect }: {
  well: Well; selected: boolean; onSelect: (id: string) => void
}) {
  return (
    <CircleMarker
      center={[well.latitude, well.longitude]}
      radius={selected ? 8 : 4.5}
      bubblingMouseEvents={false}
      pathOptions={{
        color: selected ? '#7c2d12' : '#075985',
        weight: selected ? 2.5 : 1,
        fillColor: selected ? '#f59e0b' : '#0ea5e9',
        fillOpacity: selected ? 1 : 0.7,
      }}
      eventHandlers={{ click: () => onSelect(well.well_id) }}
    />
  )
})
export default WellMarker
