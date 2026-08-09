import type { SocketStatus } from '../hooks/useTrainSocket'

interface HeaderProps {
  wsStatus: SocketStatus
}

const WS_STATUS_LABEL: Record<SocketStatus, string> = {
  connecting: 'connecting…',
  open: 'live',
  closed: 'disconnected — retrying…',
}

export function Header({ wsStatus }: HeaderProps) {
  return (
    <div id="app-header">
      <div className="wordmark-row">
        <span className="wordmark">Tashmetrio</span>
        <span className="ws-indicator" title={WS_STATUS_LABEL[wsStatus]}>
          {wsStatus !== 'open' && <span className="ws-label">{WS_STATUS_LABEL[wsStatus]}</span>}
          <span className={`ws-dot ws-dot-${wsStatus}`} />
        </span>
      </div>
      <div className="subtitle">Tashkent Metro — Live · simulated positions over OSM-derived topology</div>
    </div>
  )
}
