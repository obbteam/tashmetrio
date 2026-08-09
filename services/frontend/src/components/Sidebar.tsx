import type { SocketStatus } from '../hooks/useTrainSocket'
import type { LineTopology, StationSummary } from '../types/topology'
import { Legend } from './Legend'
import { StationDetail } from './StationDetail'
import { StatsBar } from './StatsBar'

interface SidebarProps {
  topologyError: string | null
  wsStatus: SocketStatus
  lines: LineTopology[]
  stationCount: number
  trainCount: number
  hiddenLineIds: Set<string>
  onToggleLine: (lineId: string) => void
  selectedStation: StationSummary | null
}

const WS_STATUS_LABEL: Record<SocketStatus, string> = {
  connecting: 'connecting…',
  open: 'live',
  closed: 'disconnected — retrying…',
}

export function Sidebar({
  topologyError,
  wsStatus,
  lines,
  stationCount,
  trainCount,
  hiddenLineIds,
  onToggleLine,
  selectedStation,
}: SidebarProps) {
  const statusMessage = topologyError
    ? `Topology load failed: ${topologyError}`
    : lines.length === 0
      ? 'Loading topology…'
      : `${lines.length} line(s), ${stationCount} station(s) loaded.`

  return (
    <div id="sidebar">
      <h1>Tashkent Metro — Live</h1>
      <div className="subtitle">Simulated train positions over OSM-derived topology</div>

      <div id="status" style={{ color: topologyError ? '#e26a6a' : undefined }}>
        {statusMessage}
      </div>

      <div className="ws-status">
        <span className={`ws-dot ws-dot-${wsStatus}`} />
        {WS_STATUS_LABEL[wsStatus]}
      </div>

      <StatsBar lineCount={lines.length} stationCount={stationCount} trainCount={trainCount} />

      <Legend lines={lines} hiddenLineIds={hiddenLineIds} onToggle={onToggleLine} />

      <StationDetail station={selectedStation} lines={lines} />
    </div>
  )
}
