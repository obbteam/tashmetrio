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

  const { trains, status: wsStatus } = useTrainSocket()

  useEffect(() => {
    fetchTopology()
      .then(setLines)
      .catch((error: Error) => setTopologyError(error.message))
  }, [])

  const stations = useMemo(() => summarizeStations(lines), [lines])

  function toggleLine(lineId: string) {
    setHiddenLineIds((prev) => {
      const next = new Set(prev)
      if (next.has(lineId)) next.delete(lineId)
      else next.add(lineId)
      return next
    })
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
      />
      <div id="map-wrap">
        <MapView
          lines={lines}
          stations={stations}
          trains={trains}
          hiddenLineIds={hiddenLineIds}
          onStationSelect={setSelectedStation}
        />
      </div>
    </div>
  )
}

export default App
