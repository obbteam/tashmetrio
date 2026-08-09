import { useAnimatedNumber } from '../hooks/useAnimatedNumber'

interface NetworkHealthProps {
  delayedCount: number
  cancelledCount: number
}

export function NetworkHealth({ delayedCount, cancelledCount }: NetworkHealthProps) {
  const delayed = useAnimatedNumber(delayedCount)
  const cancelled = useAnimatedNumber(cancelledCount)

  if (delayedCount === 0 && cancelledCount === 0) {
    return <div id="network-health" className="nh-clear">All trains on time</div>
  }

  return (
    <div id="network-health">
      {delayedCount > 0 && <span className="nh-badge nh-delayed">{delayed} delayed</span>}
      {cancelledCount > 0 && <span className="nh-badge nh-cancelled">{cancelled} cancelled</span>}
    </div>
  )
}
