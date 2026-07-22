#!/usr/bin/env python3
"""
Fetch Tashkent Metro topology (stations + line geometry) from OpenStreetMap
via the Overpass API and write it out as GeoJSON.

Output:
  stations.geojson       - Point features, one per station
  lines.geojson          - LineString features, one per physical line
  line_stations.json     - Per-line ordered station sequence + inter-station
                            distances (meters), ready to seed LINE_STATION rows

Usage:
    pip install requests   # (not actually required -- uses stdlib urllib)
    python fetch_tashkent_metro_osm.py [--out-dir ./osm_data]

How this works (important -- read before debugging further):
- OSM's public-transport schema splits each metro line into TWO route
  relations, one per direction, distinguished by a shared `ref` tag
  (e.g. ref=1 for both directions of the Chilonzor line). We dedupe to one
  relation per `ref` and treat that as "the line".
- A route relation's `role=stop` members are bare stop-position nodes with
  NO name tag -- they mark where a train stops on the track, not the
  station itself. Named station entities are separate nodes in OSM
  (railway=station / station=subway) that are NOT direct members of the
  route relation in a name-bearing way in this dataset.
- So station names/positions are fetched via a SEPARATE query, then
  "snapped" onto each line's route geometry (the `role=""` way members,
  stitched into a continuous polyline) by finding the nearest point along
  the line and using that arc-length to determine sequence order.
- This is more robust than trying to read station order directly out of
  route relation member lists, which vary in completeness/quality across
  cities in OSM.
"""

import argparse
import json
import math
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Bounding box around Tashkent city (south, west, north, east). Generous on
# purpose -- covers the full metro network plus margin. A bbox is used
# instead of an OSM area/boundary lookup because admin boundary tagging
# (name string, admin_level) varies enough between countries that it's an
# unreliable filter; a bbox is unambiguous.
TASHKENT_BBOX = (41.15, 69.05, 41.42, 69.45)  # south, west, north, east

# Max distance (meters) a named station node can be from a line's route
# geometry to be considered "on" that line. Real transfer stations sit
# almost exactly on the line; this catches minor OSM misalignment.
STATION_SNAP_THRESHOLD_M = 50

QUERY_ROUTES = """
[out:json][timeout:180];
(
  relation["route"="subway"]({south},{west},{north},{east});
);
out body;
>;
out skel qt;
""".format(
    south=TASHKENT_BBOX[0], west=TASHKENT_BBOX[1],
    north=TASHKENT_BBOX[2], east=TASHKENT_BBOX[3],
)

QUERY_STATIONS = """
[out:json][timeout:180];
(
  nwr["railway"="station"]["station"="subway"]({south},{west},{north},{east});
  nwr["public_transport"="station"]["station"="subway"]({south},{west},{north},{east});
);
out center;
""".format(
    south=TASHKENT_BBOX[0], west=TASHKENT_BBOX[1],
    north=TASHKENT_BBOX[2], east=TASHKENT_BBOX[3],
)


def fetch_overpass(query: str, retries: int = 3) -> dict:
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=body,
        method="POST",
        headers={
            "User-Agent": "tashmetrio-topology-fetch/0.2 (dev script; contact: none)",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            last_err = e
            print(f"[warn] Overpass request failed (attempt {attempt}/{retries}): {e}",
                  file=sys.stderr)
            time.sleep(5 * attempt)
    raise RuntimeError(f"Overpass API unreachable after {retries} attempts: {last_err}")


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def index_elements(osm_json: dict):
    nodes, ways, relations = {}, {}, {}
    for el in osm_json.get("elements", []):
        if el["type"] == "node":
            nodes[el["id"]] = el
        elif el["type"] == "way":
            ways[el["id"]] = el
        elif el["type"] == "relation":
            relations[el["id"]] = el
    return nodes, ways, relations


def dedupe_lines_by_ref(relations: dict) -> dict:
    """
    Each physical line has two route relations (one per direction) sharing
    a `ref` tag. Keep one relation per ref.
    """
    by_ref = {}
    for rel in relations.values():
        tags = rel.get("tags", {})
        if tags.get("route") != "subway":
            continue
        ref = tags.get("ref") or tags.get("name") or str(rel["id"])
        if ref not in by_ref:
            by_ref[ref] = rel
    return by_ref


def stitch_line_geometry(rel: dict, ways: dict, nodes: dict):
    """
    Build a continuous ordered polyline for a route relation by stitching
    together its path ways (role == "", the physical track geometry --
    distinct from role == "platform" members). Ways are joined by matching
    shared endpoint node IDs. Returns a list of (lat, lon) tuples.
    """
    path_way_ids = [m["ref"] for m in rel.get("members", [])
                     if m["type"] == "way" and m.get("role", "") == ""]
    segments = []
    for wid in path_way_ids:
        way = ways.get(wid)
        if not way:
            continue
        node_ids = way.get("nodes", [])
        pts = [n for n in node_ids if n in nodes]
        if len(pts) < 2:
            continue
        segments.append(pts)

    if not segments:
        return []

    # Greedy stitching: start with the first segment, repeatedly attach any
    # remaining segment whose start/end matches the current chain's ends.
    chain = list(segments.pop(0))
    changed = True
    while segments and changed:
        changed = False
        for i, seg in enumerate(segments):
            if seg[0] == chain[-1]:
                chain.extend(seg[1:])
                segments.pop(i)
                changed = True
                break
            elif seg[-1] == chain[-1]:
                chain.extend(list(reversed(seg))[1:])
                segments.pop(i)
                changed = True
                break
            elif seg[-1] == chain[0]:
                chain[0:0] = seg[:-1]
                segments.pop(i)
                changed = True
                break
            elif seg[0] == chain[0]:
                chain[0:0] = list(reversed(seg))[:-1]
                segments.pop(i)
                changed = True
                break
    if segments:
        print(f"[warn] relation {rel['id']}: {len(segments)} way segment(s) could not "
              f"be stitched into the main chain (disconnected geometry) -- geometry "
              f"may have gaps", file=sys.stderr)

    return [(nodes[nid]["lat"], nodes[nid]["lon"]) for nid in chain if nid in nodes]


def _project_onto_segment(p, a, b):
    """Local planar projection (meters) of point p onto segment a->b."""
    lat0 = math.radians(a[0])
    def to_xy(pt):
        x = math.radians(pt[1] - a[1]) * math.cos(lat0) * 6371000
        y = math.radians(pt[0] - a[0]) * 6371000
        return x, y
    ax, ay = to_xy(a)
    bx, by = to_xy(b)
    px, py = to_xy(p)
    dx, dy = bx - ax, by - ay
    seg_len2 = dx * dx + dy * dy
    t = 0.0 if seg_len2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len2))
    proj_x, proj_y = ax + t * dx, ay + t * dy
    dist = math.hypot(px - proj_x, py - proj_y)
    return t, dist


def project_point_to_polyline(point, polyline):
    """Returns (min_distance_m, arc_length_m_at_projection) for point onto polyline."""
    if len(polyline) < 2:
        return None
    best_dist = None
    best_arc = None
    cum = 0.0
    for i in range(len(polyline) - 1):
        a, b = polyline[i], polyline[i + 1]
        seg_len = haversine_m(a[0], a[1], b[0], b[1])
        t, dist = _project_onto_segment(point, a, b)
        arc = cum + t * seg_len
        if best_dist is None or dist < best_dist:
            best_dist, best_arc = dist, arc
        cum += seg_len
    return best_dist, best_arc


def station_coords(el):
    """Nodes have lat/lon directly; ways/relations only have a `center`
    (requires `out center;` in the query) since they're not single points."""
    if "lat" in el and "lon" in el:
        return el["lat"], el["lon"]
    center = el.get("center")
    if center:
        return center["lat"], center["lon"]
    return None


def station_display_name(node):
    tags = node.get("tags", {})
    return tags.get("name:en") or tags.get("name")


def build_lines(relations_by_ref, ways, nodes, stations):
    """
    For each physical line: stitch geometry, snap named stations onto it,
    sort by arc length -> ordered station sequence.
    """
    lines = []
    for ref, rel in sorted(relations_by_ref.items()):
        tags = rel.get("tags", {})
        name = tags.get("name:en") or tags.get("name") or f"line-{ref}"
        color = tags.get("colour") or tags.get("color")

        polyline = stitch_line_geometry(rel, ways, nodes)
        if not polyline:
            print(f"[warn] line '{name}' (ref {ref}): could not build route "
                  f"geometry, skipping station snapping", file=sys.stderr)
            lines.append({"ref": ref, "name": name, "color_hex": color,
                          "polyline": [], "stations": []})
            continue

        snapped = []
        for sid, s in stations.items():
            result = project_point_to_polyline((s["lat"], s["lon"]), polyline)
            if result is None:
                continue
            dist, arc = result
            if dist <= STATION_SNAP_THRESHOLD_M:
                snapped.append({
                    "osm_id": sid,
                    "name": s["name"],
                    "lat": s["lat"],
                    "lon": s["lon"],
                    "arc_length_m": arc,
                    "snap_distance_m": dist,
                })

        snapped.sort(key=lambda x: x["arc_length_m"])
        # Dedupe stations that might match at nearly the same arc length
        # (shouldn't normally happen, but guards against duplicate OSM nodes)
        deduped = []
        seen_names = set()
        for s in snapped:
            if s["name"] in seen_names:
                continue
            seen_names.add(s["name"])
            deduped.append(s)

        if not deduped:
            print(f"[warn] line '{name}' (ref {ref}): 0 stations snapped within "
                  f"{STATION_SNAP_THRESHOLD_M}m -- check STATION_SNAP_THRESHOLD_M "
                  f"or verify the station query is matching this city's tagging",
                  file=sys.stderr)

        lines.append({
            "ref": ref, "name": name, "color_hex": color,
            "polyline": polyline, "stations": deduped,
        })
    return lines


def build_geojson_stations(stations: dict) -> dict:
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
                "properties": {"osm_id": sid, "name": s["name"]},
            }
            for sid, s in stations.items()
        ],
    }


def build_geojson_lines(lines: list) -> dict:
    features = []
    for line in lines:
        if len(line["polyline"]) < 2:
            continue
        coords = [[lon, lat] for lat, lon in line["polyline"]]
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {"ref": line["ref"], "name": line["name"],
                           "color_hex": line["color_hex"]},
        })
    return {"type": "FeatureCollection", "features": features}


def build_line_stations_json(lines: list) -> list:
    out = []
    for line in lines:
        seq_entries = []
        stations = line["stations"]
        for i, s in enumerate(stations):
            distance_to_next_m = None
            if i < len(stations) - 1:
                nxt = stations[i + 1]
                distance_to_next_m = round(haversine_m(s["lat"], s["lon"], nxt["lat"], nxt["lon"]))
            seq_entries.append({
                "sequence": i,
                "station_name": s["name"],
                "station_osm_id": s["osm_id"],
                "distance_to_next_m": distance_to_next_m,
            })
        out.append({
            "line_ref": line["ref"],
            "line_name": line["name"],
            "color_hex": line["color_hex"],
            "stations": seq_entries,
        })
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="./osm_data")
    args = parser.parse_args()

    import os
    os.makedirs(args.out_dir, exist_ok=True)

    print("[info] querying Overpass for route relations + geometry...", file=sys.stderr)
    routes_json = fetch_overpass(QUERY_ROUTES)
    nodes, ways, relations = index_elements(routes_json)
    print(f"[info] fetched {len(nodes)} nodes, {len(ways)} ways, "
          f"{len(relations)} relations", file=sys.stderr)

    relations_by_ref = dedupe_lines_by_ref(relations)
    print(f"[info] deduped to {len(relations_by_ref)} physical line(s): "
          f"{list(relations_by_ref.keys())}", file=sys.stderr)

    if not relations_by_ref:
        print("[error] no subway route relations matched. Check the bbox or "
              "run the debug query from chat manually on overpass-turbo.eu",
              file=sys.stderr)
        sys.exit(1)

    print("[info] querying Overpass for named station nodes...", file=sys.stderr)
    stations_json = fetch_overpass(QUERY_STATIONS)
    station_nodes, station_ways, station_rels = index_elements(stations_json)
    stations = {}
    for etype, eldict in (("node", station_nodes), ("way", station_ways), ("relation", station_rels)):
        for eid, el in eldict.items():
            name = station_display_name(el)
            coords = station_coords(el)
            if not name or not coords:
                continue
            lat, lon = coords
            stations[f"{etype}/{eid}"] = {"name": name, "lat": lat, "lon": lon}
    print(f"[info] fetched {len(stations)} named station element(s) "
          f"(nodes + ways + relations)", file=sys.stderr)

    if not stations:
        print("[error] no named station nodes found. This city's stations may "
              "use different tags -- try railway=stop or public_transport=stop_position "
              "instead of station=subway.", file=sys.stderr)
        sys.exit(1)

    lines = build_lines(relations_by_ref, ways, nodes, stations)

    stations_geojson = build_geojson_stations(stations)
    lines_geojson = build_geojson_lines(lines)
    line_stations = build_line_stations_json(lines)

    with open(f"{args.out_dir}/stations.geojson", "w", encoding="utf-8") as f:
        json.dump(stations_geojson, f, ensure_ascii=False, indent=2)
    with open(f"{args.out_dir}/lines.geojson", "w", encoding="utf-8") as f:
        json.dump(lines_geojson, f, ensure_ascii=False, indent=2)
    with open(f"{args.out_dir}/line_stations.json", "w", encoding="utf-8") as f:
        json.dump(line_stations, f, ensure_ascii=False, indent=2)

    total_seq_stations = sum(len(l["stations"]) for l in lines)
    print(f"[info] wrote {len(stations)} named stations, {len(lines)} lines "
          f"({total_seq_stations} line-station assignments) to {args.out_dir}/",
          file=sys.stderr)
    print("[info] next: open line_stations.json and verify each line's station "
          "count/order against the official map. Also sanity check "
          "snap_distance_m isn't shown but was thresholded at "
          f"{STATION_SNAP_THRESHOLD_M}m internally.", file=sys.stderr)


if __name__ == "__main__":
    main()