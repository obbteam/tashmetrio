import type { LineTopology, StationSummary } from '../types/topology'

interface StationDetailProps {
  station: StationSummary | null
  lines: LineTopology[]
}

export function StationDetail({ station, lines }: StationDetailProps) {
  if (!station) {
    return (
      <div className="detail-panel">
        <div className="st-hint">Click a station or train for details.</div>
      </div>
    )
  }

  const lineNames = station.lineIds
    .map((id) => lines.find((line) => line.line_id === id)?.name)
    .filter((name): name is string => Boolean(name))

  return (
    <div className="detail-panel">
      <div className="st-name">{station.name}</div>
      <div className="st-hint" style={{ marginTop: 4 }}>
        Line(s): {lineNames.length ? lineNames.join(', ') : 'unknown'}
      </div>
    </div>
  )
}
