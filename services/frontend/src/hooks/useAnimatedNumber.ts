import { useEffect, useRef, useState } from 'react'

const DEFAULT_DURATION_MS = 400

export function useAnimatedNumber(target: number, durationMs: number = DEFAULT_DURATION_MS): number {
  const [display, setDisplay] = useState(target)
  const displayRef = useRef(target)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    if (displayRef.current === target) return

    const from = displayRef.current
    const start = performance.now()

    function tick(now: number) {
      const t = Math.min((now - start) / durationMs, 1)
      const eased = 1 - (1 - t) * (1 - t)
      const value = Math.round(from + (target - from) * eased)
      displayRef.current = value
      setDisplay(value)
      if (t < 1) rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current)
    }
  }, [target, durationMs])

  return display
}
