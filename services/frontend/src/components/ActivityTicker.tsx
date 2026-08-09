import type { ActivityEvent } from '../hooks/useTrainSocket'
import type { LineTopology } from '../types/topology'

interface ActivityTickerProps {
  events: ActivityEvent[]
  lines: LineTopology[]
}

export function ActivityTicker({ events, lines }: ActivityTickerProps) {
  return (
    <div id="activity-ticker">
      <div className="at-title">Activity</div>
      {events.length === 0 ? (
        <div className="at-empty">No activity yet.</div>
      ) : (
        <div className="at-list">
          {events.map((event) => {
            const lineName = lines.find((l) => l.line_id === event.line_id)?.name ?? 'Unknown line'
            return (
              <div key={event.id} className="at-row">
                <span className="at-dot" />
                <span className="at-text">{describeEvent(event, lineName)}</span>
                <span className="at-time">{relativeTime(event.at)}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function describeEvent(event: ActivityEvent, lineName: string): string {
  const trainLabel = `Train ${event.train_id.slice(0, 8)}`

  if (event.kind === 'trip_finished') {
    return `${trainLabel} finished its run on ${lineName}`
  }
  if (event.to_status === 'DELAYED') return `${trainLabel} delayed on ${lineName}`
  if (event.to_status === 'CANCELLED') return `${trainLabel} cancelled on ${lineName}`
  return `${trainLabel} back on time on ${lineName}`
}

function relativeTime(at: number): string {
  const seconds = Math.max(0, Math.round((Date.now() - at) / 1000))
  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  return `${hours}h ago`
}
