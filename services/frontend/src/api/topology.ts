import type { LineTopology } from '../types/topology'

export async function fetchTopology(): Promise<LineTopology[]> {
  const res = await fetch(import.meta.env.VITE_TOPOLOGY_URL)
  if (!res.ok) {
    throw new Error(`Topology request failed: ${res.status} ${res.statusText}`)
  }
  return res.json()
}
