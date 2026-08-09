import type { LineTopology } from '../types/topology'
import type { TrainPositionData, TripStatus } from '../types/trainPosition'

interface TrainDetailProps {
  train: TrainPositionData
  lines: LineTopology[]
  isFollowing: boolean
  onStopFollowing: () => void
}

const STATUS_LABEL: Record<TripStatus, string> = {
  'ON TIME': 'On time',
  DELAYED: 'Delayed',
  CANCELLED: 'Cancelled',
}

const STATUS_CLASS: Record<TripStatus, string> = {
  'ON TIME': 'status-ontime',
  DELAYED: 'status-delayed',
  CANCELLED: 'status-cancelled',
}

export function TrainDetail({ train, lines, isFollowing, onStopFollowing }: TrainDetailProps) {
  const line = lines.find((l) => l.line_id === train.line_id)
  const progress = Math.min(Math.max(train.progress_pct, 0), 100)

  return (
    <div className="detail-panel">
      <div className="td-head">
        <span className="swatch" style={{ background: line?.color_hex || '#888' }} />
        <div className="td-name">Train {train.train_id.slice(0, 8)}</div>
        <span className={`status-badge ${STATUS_CLASS[train.trip_status]}`}>
          {STATUS_LABEL[train.trip_status]}
        </span>
      </div>
      <div className="td-line">{line?.name ?? 'Unknown line'}</div>

      <div className="td-progress-row">
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <div className="progress-pct">{Math.round(progress)}%</div>
      </div>

      <div className="td-eta">ETA — not yet available</div>

      {isFollowing && (
        <button type="button" className="stop-tracking-btn" onClick={onStopFollowing}>
          Stop tracking
        </button>
      )}
    </div>
  )
}
