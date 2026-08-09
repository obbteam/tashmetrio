import { useAnimatedNumber } from '../hooks/useAnimatedNumber'

interface StatsBarProps {
  lineCount: number
  stationCount: number
  trainCount: number
}

export function StatsBar({ lineCount, stationCount, trainCount }: StatsBarProps) {
  const animatedLineCount = useAnimatedNumber(lineCount)
  const animatedStationCount = useAnimatedNumber(stationCount)
  const animatedTrainCount = useAnimatedNumber(trainCount)

  return (
    <div id="stats-bar">
      <div className="stat-chip">
        <div className="stat-value">{lineCount ? animatedLineCount : '–'}</div>
        <div className="stat-label">Lines</div>
      </div>
      <div className="stat-chip">
        <div className="stat-value">{stationCount ? animatedStationCount : '–'}</div>
        <div className="stat-label">Stations</div>
      </div>
      <div className="stat-chip">
        <div className="stat-value">{trainCount ? animatedTrainCount : '–'}</div>
        <div className="stat-label">Live trains</div>
      </div>
    </div>
  )
}
