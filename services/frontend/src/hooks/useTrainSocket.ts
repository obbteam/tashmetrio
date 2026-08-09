import { useEffect, useRef, useState } from 'react'
import type { TrainPositionData, TrainSocketMessage, TripStatus } from '../types/trainPosition'

export type SocketStatus = 'connecting' | 'open' | 'closed'

const RECONNECT_DELAY_MS = 2000
const MAX_EVENTS = 25

export type ActivityEventKind = 'trip_finished' | 'status_changed'

export interface ActivityEvent {
  id: string
  at: number
  kind: ActivityEventKind
  train_id: string
  line_id: string
  from_status?: TripStatus
  to_status?: TripStatus
}

export function useTrainSocket() {
  const [status, setStatus] = useState<SocketStatus>('connecting')
  const [trainsById, setTrainsById] = useState<Map<string, TrainPositionData>>(new Map())
  const [snapshotVersion, setSnapshotVersion] = useState(0)
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const trainsByIdRef = useRef(trainsById)
  const eventIdRef = useRef(0)
  trainsByIdRef.current = trainsById

  function pushEvent(event: Omit<ActivityEvent, 'id' | 'at'>) {
    eventIdRef.current += 1
    const entry: ActivityEvent = { ...event, id: `${eventIdRef.current}`, at: Date.now() }
    setEvents((prev) => [entry, ...prev].slice(0, MAX_EVENTS))
  }

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
          setSnapshotVersion((v) => v + 1)
          return
        }

        if (message.update_type === 'trip_finished') {
          const next = new Map(trainsByIdRef.current)
          const finished = next.get(message.update_data.train_id)
          next.delete(message.update_data.train_id)
          setTrainsById(next)
          pushEvent({
            kind: 'trip_finished',
            train_id: message.update_data.train_id,
            line_id: (finished ?? message.update_data).line_id,
          })
          return
        }

        const previous = trainsByIdRef.current.get(message.update_data.train_id)
        const next = new Map(trainsByIdRef.current)
        next.set(message.update_data.train_id, message.update_data)
        setTrainsById(next)

        if (previous && previous.trip_status !== message.update_data.trip_status) {
          pushEvent({
            kind: 'status_changed',
            train_id: message.update_data.train_id,
            line_id: message.update_data.line_id,
            from_status: previous.trip_status,
            to_status: message.update_data.trip_status,
          })
        }
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

  return { trains: Array.from(trainsById.values()), status, snapshotVersion, events }
}
