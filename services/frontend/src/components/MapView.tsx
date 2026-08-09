import {
  GeoJSONSource,
  LngLatBounds,
  MapLibreMap,
  NavigationControl,
  type LngLatBoundsLike,
  type MapLayerMouseEvent,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { LineTopology, StationSummary } from '../types/topology'
import type { TrainPositionData, TripStatus } from '../types/trainPosition'

const LINES_SOURCE = 'metro-lines'
const STATIONS_SOURCE = 'metro-stations'
const TRAINS_SOURCE = 'metro-trains'

const FOCUS_COLOR = '#8b7cf6'
const ACCENT_COLOR = '#ffb454'
const CANCELLED_COLOR = '#e26a6a'
const BG_COLOR = '#0a0c10'

const MIN_TWEEN_MS = 120
const MAX_TWEEN_MS = 1500
const DEFAULT_TWEEN_MS = 250

interface TrainTween {
  from: [number, number]
  to: [number, number]
  start: number
  duration: number
  line_id: string
  trip_status: TripStatus
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function interpolateTween(tween: TrainTween, now: number): [number, number] {
  const t = clamp((now - tween.start) / tween.duration, 0, 1)
  return [
    tween.from[0] + (tween.to[0] - tween.from[0]) * t,
    tween.from[1] + (tween.to[1] - tween.from[1]) * t,
  ]
}

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
  onTrainSelect: (trainId: string) => void
  onBackgroundClick: () => void
  selectedTrainId: string | null
  isFollowing: boolean
  onFollowingChange: (following: boolean) => void
  snapshotVersion: number
}

export function MapView({
  lines,
  stations,
  trains,
  hiddenLineIds,
  onStationSelect,
  onTrainSelect,
  onBackgroundClick,
  selectedTrainId,
  isFollowing,
  onFollowingChange,
  snapshotVersion,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const [mapLoaded, setMapLoaded] = useState(false)

  const stationsRef = useRef(stations)
  const onStationSelectRef = useRef(onStationSelect)
  const onTrainSelectRef = useRef(onTrainSelect)
  const onBackgroundClickRef = useRef(onBackgroundClick)
  const onFollowingChangeRef = useRef(onFollowingChange)
  const hiddenLineIdsRef = useRef(hiddenLineIds)
  const selectedTrainIdRef = useRef(selectedTrainId)
  const isFollowingRef = useRef(isFollowing)
  stationsRef.current = stations
  onStationSelectRef.current = onStationSelect
  onTrainSelectRef.current = onTrainSelect
  onBackgroundClickRef.current = onBackgroundClick
  onFollowingChangeRef.current = onFollowingChange
  hiddenLineIdsRef.current = hiddenLineIds
  selectedTrainIdRef.current = selectedTrainId
  isFollowingRef.current = isFollowing

  const colorByLine = useMemo(
    () => new Map(lines.map((line) => [line.line_id, line.color_hex])),
    [lines],
  )
  const colorByLineRef = useRef(colorByLine)
  colorByLineRef.current = colorByLine

  const tweensRef = useRef(new Map<string, TrainTween>())
  const lastUpdateAtRef = useRef(new Map<string, number>())
  const lastSnapshotVersionRef = useRef(snapshotVersion)

  const selectedLineId = useMemo(
    () => trains.find((t) => t.train_id === selectedTrainId)?.line_id ?? null,
    [trains, selectedTrainId],
  )

  useEffect(() => {
    if (!containerRef.current) return

    const map = new MapLibreMap({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {},
        layers: [{ id: 'background', type: 'background', paint: { 'background-color': BG_COLOR } }],
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
        id: 'route-highlight-layer',
        type: 'line',
        source: LINES_SOURCE,
        filter: ['==', ['get', 'line_id'], '__none__'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': FOCUS_COLOR,
          'line-width': 9,
          'line-opacity': 0.35,
          'line-blur': 1,
        },
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
          'circle-stroke-color': BG_COLOR,
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
          'text-halo-color': BG_COLOR,
          'text-halo-width': 1,
        },
      })
      map.addLayer({
        id: 'trains-halo-layer',
        type: 'circle',
        source: TRAINS_SOURCE,
        filter: ['==', ['get', 'trip_status'], 'DELAYED'],
        paint: {
          'circle-radius': ['+', 9, ['*', ['get', 'pulse'], 7]],
          'circle-color': ACCENT_COLOR,
          'circle-opacity': ['*', 0.4, ['-', 1, ['get', 'pulse']]],
        },
      })
      map.addLayer({
        id: 'trains-layer',
        type: 'circle',
        source: TRAINS_SOURCE,
        paint: {
          'circle-radius': 6,
          'circle-color': [
            'case',
            ['==', ['get', 'trip_status'], 'CANCELLED'],
            CANCELLED_COLOR,
            ['get', 'color_hex'],
          ],
          'circle-opacity': ['case', ['==', ['get', 'trip_status'], 'CANCELLED'], 0.45, 1],
          'circle-stroke-color': BG_COLOR,
          'circle-stroke-width': 1.5,
        },
      })
      map.addLayer({
        id: 'trains-selected-ring-layer',
        type: 'circle',
        source: TRAINS_SOURCE,
        filter: ['get', 'selected'],
        paint: {
          'circle-radius': 11,
          'circle-color': 'rgba(0,0,0,0)',
          'circle-stroke-color': FOCUS_COLOR,
          'circle-stroke-width': 2,
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

      map.on('mouseenter', 'trains-layer', () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', 'trains-layer', () => {
        map.getCanvas().style.cursor = ''
      })
      map.on('click', 'trains-layer', (event: MapLayerMouseEvent) => {
        const feature = event.features?.[0]
        const trainId = feature?.properties?.train_id
        if (typeof trainId === 'string') onTrainSelectRef.current(trainId)
      })

      map.on('click', (event: MapLayerMouseEvent) => {
        const hits = map.queryRenderedFeatures(event.point, {
          layers: ['stations-layer', 'trains-layer'],
        })
        if (hits.length === 0) onBackgroundClickRef.current()
      })

      map.on('dragstart', () => onFollowingChangeRef.current(false))
      map.on('zoomstart', () => onFollowingChangeRef.current(false))

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
    const layer = map.getLayer('route-highlight-layer')
    if (!layer) return
    map.setFilter('route-highlight-layer', ['==', ['get', 'line_id'], selectedLineId ?? '__none__'])
  }, [selectedLineId, mapLoaded])

  // Sync incoming train positions into per-train tween state. A fresh
  // snapshot (initial connect / reconnect) discards prior tweens so every
  // train snaps into place instead of animating in from nowhere.
  useEffect(() => {
    if (!mapLoaded) return
    const tweens = tweensRef.current
    const lastUpdateAt = lastUpdateAtRef.current
    const now = performance.now()

    if (snapshotVersion !== lastSnapshotVersionRef.current) {
      tweens.clear()
      lastUpdateAt.clear()
      lastSnapshotVersionRef.current = snapshotVersion
    }

    const seenIds = new Set<string>()
    for (const train of trains) {
      seenIds.add(train.train_id)
      const to: [number, number] = [train.position.longitude, train.position.latitude]
      const existing = tweens.get(train.train_id)
      const from = existing ? interpolateTween(existing, now) : to
      const prevAt = lastUpdateAt.get(train.train_id)
      const duration = prevAt ? clamp(now - prevAt, MIN_TWEEN_MS, MAX_TWEEN_MS) : DEFAULT_TWEEN_MS
      tweens.set(train.train_id, {
        from,
        to,
        start: now,
        duration,
        line_id: train.line_id,
        trip_status: train.trip_status,
      })
      lastUpdateAt.set(train.train_id, now)
    }

    for (const id of Array.from(tweens.keys())) {
      if (!seenIds.has(id)) {
        tweens.delete(id)
        lastUpdateAt.delete(id)
      }
    }
  }, [trains, snapshotVersion, mapLoaded])

  // Single animation loop drives train rendering: position interpolation,
  // the delayed-status pulse, and camera-follow all read from refs here so
  // none of this depends on React re-renders.
  useEffect(() => {
    if (!mapLoaded) return
    const map = mapRef.current
    if (!map) return

    let frameId: number

    function frame(now: number) {
      const source = map!.getSource(TRAINS_SOURCE) as GeoJSONSource | undefined
      if (source) {
        const pulse = (Math.sin(now / 260) + 1) / 2
        const hidden = hiddenLineIdsRef.current
        const colorByLine = colorByLineRef.current
        const selectedId = selectedTrainIdRef.current
        const following = isFollowingRef.current
        const features: GeoJSON.Feature[] = []
        let followPos: [number, number] | null = null

        tweensRef.current.forEach((tween, trainId) => {
          if (hidden.has(tween.line_id)) return
          const pos = interpolateTween(tween, now)
          const selected = trainId === selectedId
          if (selected && following) followPos = pos
          features.push({
            type: 'Feature',
            geometry: { type: 'Point', coordinates: pos },
            properties: {
              train_id: trainId,
              line_id: tween.line_id,
              color_hex: colorByLine.get(tween.line_id) ?? '#888',
              trip_status: tween.trip_status,
              pulse,
              selected,
            },
          })
        })

        source.setData({ type: 'FeatureCollection', features })
        if (followPos) map!.setCenter(followPos)
      }

      frameId = requestAnimationFrame(frame)
    }

    frameId = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(frameId)
  }, [mapLoaded])

  return <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
}
