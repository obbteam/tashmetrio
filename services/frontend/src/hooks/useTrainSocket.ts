import { useEffect, useRef, useState } from 'react'
import type { TrainPositionData, TrainSocketMessage } from '../types/trainPosition'

export type SocketStatus = 'connecting' | 'open' | 'closed'

const RECONNECT_DELAY_MS = 2000

export function useTrainSocket() {
  const [status, setStatus] = useState<SocketStatus>('connecting')
  const [trainsById, setTrainsById] = useState<Map<string, TrainPositionData>>(new Map())
  const trainsByIdRef = useRef(trainsById)
  trainsByIdRef.current = trainsById

  useEffect(() => {
    let socket: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined
    let cancelled = false

    function connect() {
      setStatus('connecting')
      socket = new WebSocket(import.meta.env.VITE_TRAIN_WS_URL)

      socket.addEventListener('open', () => setStatus('open'))

      socket.addEventListener('message', (event) => {
        const message: TrainSocketMessage = JSON.parse(event.data)

        if ('snapshot_type' in message) {
          const next = new Map<string, TrainPositionData>()
          for (const train of message.snapshot_data) next.set(train.train_id, train)
          setTrainsById(next)
          return
        }

        if (message.update_type === 'trip_finished') {
          const next = new Map(trainsByIdRef.current)
          next.delete(message.update_data.train_id)
          setTrainsById(next)
          return
        }

        const next = new Map(trainsByIdRef.current)
        next.set(message.update_data.train_id, message.update_data)
        setTrainsById(next)
      })

      socket.addEventListener('close', () => {
        setStatus('closed')
        if (!cancelled) reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS)
      })

      socket.addEventListener('error', () => socket?.close())
    }

    connect()

    return () => {
      cancelled = true
      clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [])

  return { trains: Array.from(trainsById.values()), status }
}
