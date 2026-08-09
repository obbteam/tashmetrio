import { setWorkerUrl } from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Vite bundles maplibre-gl into a single chunk and doesn't emit its
// separate tile-processing worker alongside it, so maplibre's default
// worker URL guess 404s (silently: tiles just never finish "loading").
// Point it at the real worker bundle before any Map is constructed.
setWorkerUrl(maplibreWorkerUrl)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
