import {
  GeoJSONSource,
  LngLatBounds,
  MapLibreMap,
  NavigationControl,
  type LngLatBoundsLike,
  type MapLayerMouseEvent,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import type { LineTopology, StationSummary } from '../types/topology'
import type { TrainPositionData } from '../types/trainPosition'

const LINES_SOURCE = 'metro-lines'
const STATIONS_SOURCE = 'metro-stations'
const TRAINS_SOURCE = 'metro-trains'

function linesGeoJSON(lines: LineTopology[], hidden: Set<string>): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: lines
      .filter((line) => !hidden.has(line.line_id))
      .map((line) => ({
        type: 'Feature',
        geometry: line.geom,
        properties: { line_id: line.line_id, name: line.name, color_hex: line.color_hex },
      })),
  }
}

function stationsGeoJSON(stations: StationSummary[], hidden: Set<string>): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: stations
      .filter((station) => station.lineIds.some((lineId) => !hidden.has(lineId)))
      .map((station) => ({
        type: 'Feature',
        geometry: station.geom,
        properties: {
          station_id: station.station_id,
          name: station.name,
          interchange: station.lineIds.length > 1,
        },
      })),
  }
}

function trainsGeoJSON(
  trains: TrainPositionData[],
  colorByLine: Map<string, string>,
  hidden: Set<string>,
): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: trains
      .filter((train) => !train.is_finished && !hidden.has(train.line_id))
      .map((train) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [train.position.longitude, train.position.latitude] },
        properties: {
          train_id: train.train_id,
          color_hex: colorByLine.get(train.line_id) ?? '#ffb454',
          trip_status: train.trip_status,
        },
      })),
  }
}

function boundsOf(lines: LineTopology[]): LngLatBoundsLike | null {
  if (lines.length === 0) return null
  const bounds = new LngLatBounds()
  for (const line of lines) {
    for (const [lng, lat] of line.geom.coordinates) bounds.extend([lng, lat])
  }
  return bounds
}

interface MapViewProps {
  lines: LineTopology[]
  stations: StationSummary[]
  trains: TrainPositionData[]
  hiddenLineIds: Set<string>
  onStationSelect: (station: StationSummary) => void
}

export function MapView({ lines, stations, trains, hiddenLineIds, onStationSelect }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const [mapLoaded, setMapLoaded] = useState(false)
  const stationsRef = useRef(stations)
  const onStationSelectRef = useRef(onStationSelect)
  stationsRef.current = stations
  onStationSelectRef.current = onStationSelect

  useEffect(() => {
    if (!containerRef.current) return

    const map = new MapLibreMap({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {},
        layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#0a0c10' } }],
      },
      center: [69.2401, 41.2995],
      zoom: 10.5,
      attributionControl: false,
    })
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    mapRef.current = map

    map.on('load', () => {
      map.addSource(LINES_SOURCE, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      map.addSource(STATIONS_SOURCE, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      map.addSource(TRAINS_SOURCE, {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })

      map.addLayer({
        id: 'lines-layer',
        type: 'line',
        source: LINES_SOURCE,
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': ['get', 'color_hex'],
          'line-width': 3,
          'line-opacity': 0.85,
        },
      })
      map.addLayer({
        id: 'stations-layer',
        type: 'circle',
        source: STATIONS_SOURCE,
        paint: {
          'circle-radius': ['case', ['get', 'interchange'], 5.5, 4],
          'circle-color': '#e7e9ee',
          'circle-stroke-color': '#0a0c10',
          'circle-stroke-width': 1.5,
        },
      })
      map.addLayer({
        id: 'stations-label',
        type: 'symbol',
        source: STATIONS_SOURCE,
        layout: {
          'text-field': ['get', 'name'],
          'text-size': 10,
          'text-font': ['Noto Sans Regular'],
          'text-offset': [0, 1.1],
          'text-anchor': 'top',
          'text-optional': true,
        },
        paint: {
          'text-color': '#838a99',
          'text-halo-color': '#0a0c10',
          'text-halo-width': 1,
        },
      })
      map.addLayer({
        id: 'trains-layer',
        type: 'circle',
        source: TRAINS_SOURCE,
        paint: {
          'circle-radius': 6,
          'circle-color': ['get', 'color_hex'],
          'circle-stroke-color': '#ffb454',
          'circle-stroke-width': 1.5,
        },
      })

      map.on('mouseenter', 'stations-layer', () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', 'stations-layer', () => {
        map.getCanvas().style.cursor = ''
      })
      map.on('click', 'stations-layer', (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0]
        const stationId = feature?.properties?.station_id
        const station = stationsRef.current.find((s) => s.station_id === stationId)
        if (station) onStationSelectRef.current(station)
      })

      setMapLoaded(true)
    })

    return () => {
      setMapLoaded(false)
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapLoaded) return
    const source = map.getSource(LINES_SOURCE) as GeoJSONSource | undefined
    source?.setData(linesGeoJSON(lines, hiddenLineIds))
  }, [lines, hiddenLineIds, mapLoaded])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapLoaded) return
    const bounds = boundsOf(lines)
    if (bounds) map.fitBounds(bounds, { padding: 60, duration: 0 })
    // Deliberately excludes hiddenLineIds: toggling a line in the legend
    // shouldn't re-center/re-zoom the map.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lines, mapLoaded])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapLoaded) return
    const source = map.getSource(STATIONS_SOURCE) as GeoJSONSource | undefined
    source?.setData(stationsGeoJSON(stations, hiddenLineIds))
  }, [stations, hiddenLineIds, mapLoaded])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapLoaded) return
    const colorByLine = new Map(lines.map((line) => [line.line_id, line.color_hex]))
    const source = map.getSource(TRAINS_SOURCE) as GeoJSONSource | undefined
    source?.setData(trainsGeoJSON(trains, colorByLine, hiddenLineIds))
  }, [trains, lines, hiddenLineIds, mapLoaded])

  return <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
}
