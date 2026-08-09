import type { ActivityEvent, SocketStatus } from '../hooks/useTrainSocket'
import type { LineTopology, StationSummary } from '../types/topology'
import type { TrainPositionData } from '../types/trainPosition'
import { ActivityTicker } from './ActivityTicker'
import { Header } from './Header'
import { Legend } from './Legend'
import { NetworkHealth } from './NetworkHealth'
import { StationDetail } from './StationDetail'
import { StatsBar } from './StatsBar'
import { TrainDetail } from './TrainDetail'

interface SidebarProps {
  topologyError: string | null
  wsStatus: SocketStatus
  lines: LineTopology[]
  stationCount: number
  trainCount: number
  hiddenLineIds: Set<string>
  onToggleLine: (lineId: string) => void
  selectedStation: StationSummary | null
  selectedTrain: TrainPositionData | undefined
  isFollowing: boolean
  onStopFollowing: () => void
  networkHealth: { delayedCount: number; cancelledCount: number }
  events: ActivityEvent[]
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
  selectedTrain,
  isFollowing,
  onStopFollowing,
  networkHealth,
  events,
}: SidebarProps) {
  const statusMessage = topologyError
    ? `Topology load failed: ${topologyError}`
    : lines.length === 0
      ? 'Loading topology…'
      : `${lines.length} line(s), ${stationCount} station(s) loaded.`

  return (
    <div id="sidebar">
      <Header wsStatus={wsStatus} />

      <div id="status" style={{ color: topologyError ? '#e26a6a' : undefined }}>
        {statusMessage}
      </div>

      <StatsBar lineCount={lines.length} stationCount={stationCount} trainCount={trainCount} />

      <NetworkHealth delayedCount={networkHealth.delayedCount} cancelledCount={networkHealth.cancelledCount} />

      <Legend lines={lines} hiddenLineIds={hiddenLineIds} onToggle={onToggleLine} />

      <ActivityTicker events={events} lines={lines} />

      {selectedTrain ? (
        <TrainDetail
          train={selectedTrain}
          lines={lines}
          isFollowing={isFollowing}
          onStopFollowing={onStopFollowing}
        />
      ) : (
        <StationDetail station={selectedStation} lines={lines} />
      )}
    </div>
  )
}
