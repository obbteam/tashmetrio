import { useEffect, useMemo, useState } from 'react'
import { fetchTopology } from './api/topology'
import { MapView } from './components/MapView'
import { Sidebar } from './components/Sidebar'
import { useTrainSocket } from './hooks/useTrainSocket'
import { summarizeStations, type LineTopology, type StationSummary } from './types/topology'

function App() {
  const [lines, setLines] = useState<LineTopology[]>([])
  const [topologyError, setTopologyError] = useState<string | null>(null)
  const [hiddenLineIds, setHiddenLineIds] = useState<Set<string>>(new Set())
  const [selectedStation, setSelectedStation] = useState<StationSummary | null>(null)
  const [selectedTrainId, setSelectedTrainId] = useState<string | null>(null)
  const [isFollowing, setIsFollowing] = useState(false)

  const { trains, status: wsStatus, snapshotVersion, events } = useTrainSocket()

  useEffect(() => {
    fetchTopology()
      .then(setLines)
      .catch((error: Error) => setTopologyError(error.message))
  }, [])

  const stations = useMemo(() => summarizeStations(lines), [lines])

  const selectedTrain = useMemo(
    () => trains.find((train) => train.train_id === selectedTrainId),
    [trains, selectedTrainId],
  )

  useEffect(() => {
    if (selectedTrainId && !selectedTrain) {
      setSelectedTrainId(null)
      setIsFollowing(false)
    }
  }, [selectedTrainId, selectedTrain])

  const networkHealth = useMemo(() => {
    let delayedCount = 0
    let cancelledCount = 0
    for (const train of trains) {
      if (train.trip_status === 'DELAYED') delayedCount += 1
      else if (train.trip_status === 'CANCELLED') cancelledCount += 1
    }
    return { delayedCount, cancelledCount }
  }, [trains])

  function toggleLine(lineId: string) {
    setHiddenLineIds((prev) => {
      const next = new Set(prev)
      if (next.has(lineId)) next.delete(lineId)
      else next.add(lineId)
      return next
    })
  }

  function handleStationSelect(station: StationSummary) {
    setSelectedStation(station)
    setSelectedTrainId(null)
    setIsFollowing(false)
  }

  function handleTrainSelect(trainId: string) {
    setSelectedTrainId(trainId)
    setSelectedStation(null)
    setIsFollowing(true)
  }

  function handleBackgroundClick() {
    setSelectedStation(null)
    setSelectedTrainId(null)
    setIsFollowing(false)
  }

  return (
    <div id="app">
      <Sidebar
        topologyError={topologyError}
        wsStatus={wsStatus}
        lines={lines}
        stationCount={stations.length}
        trainCount={trains.length}
        hiddenLineIds={hiddenLineIds}
        onToggleLine={toggleLine}
        selectedStation={selectedStation}
        selectedTrain={selectedTrain}
        isFollowing={isFollowing}
        onStopFollowing={() => setIsFollowing(false)}
        networkHealth={networkHealth}
        events={events}
      />
      <div id="map-wrap">
        <MapView
          lines={lines}
          stations={stations}
          trains={trains}
          hiddenLineIds={hiddenLineIds}
          onStationSelect={handleStationSelect}
          onTrainSelect={handleTrainSelect}
          onBackgroundClick={handleBackgroundClick}
          selectedTrainId={selectedTrainId}
          isFollowing={isFollowing}
          onFollowingChange={setIsFollowing}
          snapshotVersion={snapshotVersion}
        />
      </div>
    </div>
  )
}

export default App
