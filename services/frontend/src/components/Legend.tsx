import type { LineTopology } from '../types/topology'

interface LegendProps {
  lines: LineTopology[]
  hiddenLineIds: Set<string>
  onToggle: (lineId: string) => void
}

export function Legend({ lines, hiddenLineIds, onToggle }: LegendProps) {
  return (
    <>
      <div id="legend-title">Lines</div>
      <div id="legend">
        {lines.map((line) => {
          const dimmed = hiddenLineIds.has(line.line_id)
          return (
            <div
              key={line.line_id}
              className={`legend-row${dimmed ? ' dimmed' : ''}`}
              onClick={() => onToggle(line.line_id)}
            >
              <div className="swatch" style={{ background: line.color_hex || '#888' }} />
              <div className="name">{line.name}</div>
              <div className="count">{line.stations.length}</div>
            </div>
          )
        })}
      </div>
    </>
  )
}
