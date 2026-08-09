export interface StationOnLine {
  station_id: string
  name: string
  sequence: number
  geom: GeoJSON.Point
}

export interface LineTopology {
  line_id: string
  name: string
  color_hex: string
  geom: GeoJSON.LineString
  stations: StationOnLine[]
}

export interface StationSummary {
  station_id: string
  name: string
  geom: GeoJSON.Point
  lineIds: string[]
}

export function summarizeStations(lines: LineTopology[]): StationSummary[] {
  const byId = new Map<string, StationSummary>()

  for (const line of lines) {
    for (const station of line.stations) {
      const existing = byId.get(station.station_id)
      if (existing) {
        existing.lineIds.push(line.line_id)
      } else {
        byId.set(station.station_id, {
          station_id: station.station_id,
          name: station.name,
          geom: station.geom,
          lineIds: [line.line_id],
        })
      }
    }
  }

  return Array.from(byId.values())
}
