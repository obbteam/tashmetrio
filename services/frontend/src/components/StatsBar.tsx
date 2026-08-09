interface StatsBarProps {
  lineCount: number
  stationCount: number
  trainCount: number
}

export function StatsBar({ lineCount, stationCount, trainCount }: StatsBarProps) {
  return (
    <div id="stats-bar">
      <div className="stat-chip">
        <div className="stat-value">{lineCount || '–'}</div>
        <div className="stat-label">Lines</div>
      </div>
      <div className="stat-chip">
        <div className="stat-value">{stationCount || '–'}</div>
        <div className="stat-label">Stations</div>
      </div>
      <div className="stat-chip">
        <div className="stat-value">{trainCount || '–'}</div>
        <div className="stat-label">Live trains</div>
      </div>
    </div>
  )
}
