export interface Position {
  latitude: number
  longitude: number
}

export type TripStatus = 'ON TIME' | 'DELAYED' | 'CANCELLED'

export interface TrainPositionData {
  trip_id: string
  train_id: string
  line_id: string
  current_segment_id: string
  progress_pct: number
  position: Position
  trip_status: TripStatus
  is_finished: boolean
}

export interface TrainPositionSnapshotMessage {
  snapshot_type: 'train_position_snapshot'
  snapshot_data: TrainPositionData[]
}

export interface TrainPositionUpdateMessage {
  update_type: 'train_position_update' | 'trip_finished'
  update_data: TrainPositionData
}

export type TrainSocketMessage = TrainPositionSnapshotMessage | TrainPositionUpdateMessage
