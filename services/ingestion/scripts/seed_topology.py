#!/usr/bin/env python3
"""
SKETCH -- seed the topology tables (stations, lines, line_stations) from the
OSM extraction output produced by scripts/overpass_api.py at the repo root.

Idempotent by design: re-running it after a fresh OSM fetch upserts rows
keyed on natural keys (station osm_id, line name) instead of duplicating
them, so "re-fetch OSM -> reseed" is always safe.

`lines.max_speed_mps` / `max_acceleration_mps2` have no OSM source -- they're
operator/rolling-stock knowledge that has to be hand-filled in
LINE_PERFORMANCE below. A line missing from that dict is skipped (with a
warning) rather than written with a made-up placeholder.

Known rough edge: if a re-fetch reorders stations on a line, upserting by
(line_id, station_id) can still collide with the separate
(line_id, sequence) unique constraint if two rows' sequences cross. Not
handled here -- would need a two-pass update (bump sequences out of the way
first) if that turns out to matter in practice.

Usage (from services/ingestion, with that service's venv active):
    python scripts/seed_topology.py [--osm-dir ../../osm_data]
"""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

# Make `src` importable regardless of the CWD this is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.common.database_session import session_maker
from src.adapters.common.models import Lines, LineStations, Stations

# OSM's raw line `name` embeds the route's endpoints (e.g. "Chilanzor Line:
# Chinor => Buyuk Ipak Yoli") because it comes from one of the two
# per-direction route relations that dedupe_lines_by_ref() collapsed into
# one -- it was never meant to be a display name. Map the raw name straight
# through to whatever name should actually be used going forward. All 4
# current raw names are seeded below; re-run this script and check stderr
# for "no LINE_NAME_OVERRIDES entry" warnings if a fresh OSM fetch produces
# a raw name not covered here.
LINE_NAME_OVERRIDES: dict[str, str] = {
    "Chilanzor Line: Chinor => Buyuk Ipak Yoli": "Chilanzor line",
    "Oʻzbekiston Line: Beruniy - Dustlik": "Oʻzbekiston line",
    "Yunusobod Line: Turkiston - Ming Orik": "Yunusobod line",
    "Circle Line: Kipchak - Technopark": "Circle line",
}

# Same idea for stations: OSM's `name`/`name:en` tags are inconsistent
# (mixed transliteration, Soviet-era names in parentheses, etc). Defaults to
# identity for every station currently in stations.geojson -- edit the
# values you want cleaned up, no need to touch the keys.
STATION_NAME_OVERRIDES: dict[str, str] = {
    "Abdulla Qodirii": "Abdulla Qodirii",
    "Alisher Navoiy": "Alisher Navoiy",
    "Almas": "Almas",
    "Almazar (Sabir Rakhimov)": "Almazar",
    "Amir Timur Square": "Amir Timur Square",
    "Aybek": "Aybek",
    "Badamzar": "Badamzar",
    "Beruniy": "Beruniy",
    "Buyuk Ipak Yuli (Maxim Gorky)": "Buyuk Ipak Yuli",
    "Chashtepa": "Chashtepa",
    "Chilanzar": "Chilanzar",
    "Chinara": "Chinara",
    "Chorsu": "Chorsu",
    "Cosmonauts": "Cosmonauts",
    "Drujba Narodov": "Drujba Narodov",
    "Dustlik (Chkalov)": "Dustlik",
    "Gafur Gulyam": "Gafur Gulyam",
    "Hamid Alimjan": "Hamid Alimjan",
    "Khanabad": "Khanabad",
    "Kipchak": "Kipchak",
    "Kuruvchilar (Stroiteley)": "Kuruvchilar",
    "Kuylyuk": "Kuylyuk",
    "Mashinasozlar (Tashselmash)": "Mashinasozlar",
    "Matonat": "Matonat",
    "Milliy Bog (Komsomolskaya)": "Milliy Bog",
    "Ming Urik": "Ming Urik",
    "Minor": "Minor",
    "Mirzo Ulugbek (50 years USSR)": "Mirzo Ulugbek",
    "Mustaqillik maydoni": "Mustaqillik maydoni",
    "Novza (Hamza)": "Novza",
    "Pakhtakor": "Pakhtakor",
    "Pushkin": "Pushkin",
    "Qiyot": "Qiyot",
    "Rakhat": "Rakhat",
    "Sergeli": "Sergeli",
    "Shahristan": "Shahristan",
    "Talaryk": "Talaryk",
    "Tashkent": "Tashkent",
    "Technopark": "Technopark",
    "Tinchlik": "Tinchlik",
    "Turan": "Turan",
    "Turkistan": "Turkistan",
    "Tuzel": "Tuzel",
    "Uzbekistan": "Uzbekistan",
    "Uzgarish": "Uzgarish",
    "Yangiabad": "Yangiabad",
    "Yangihayot": "Yangihayot",
    "Yashnabad": "Yashnabad",
    "Yunus Rajabiy": "Yunus Rajabiy",
    "Yunusabad": "Yunusabad",
}

# Keyed by the CLEAN line name (i.e. LINE_NAME_OVERRIDES' values, not the
# raw OSM name -- these two dicts are meant to be edited independently).
# TODO: fill in from operator conversations / rolling-stock specs.
LINE_PERFORMANCE: dict[str, dict[str, float]] = {
    "Chilanzor line": {"max_speed_mps": 20, "max_acceleration_mps2": 2.0},
    "Oʻzbekiston line": {"max_speed_mps": 20, "max_acceleration_mps2": 2.0},
    "Yunusobod line": {"max_speed_mps": 18, "max_acceleration_mps2": 2.0},
    "Circle line": {"max_speed_mps": 15, "max_acceleration_mps2": 1.5},
}


def load_osm_data(osm_dir: Path) -> tuple[dict, dict, list]:
    with open(osm_dir / "stations.geojson", encoding="utf-8") as f:
        stations_geojson = json.load(f)
    with open(osm_dir / "lines.geojson", encoding="utf-8") as f:
        lines_geojson = json.load(f)
    with open(osm_dir / "line_stations.json", encoding="utf-8") as f:
        line_stations = json.load(f)
    return stations_geojson, lines_geojson, line_stations


async def upsert_stations(
    session: AsyncSession, stations_geojson: dict
) -> dict[str, uuid.UUID]:
    """Returns {osm_id: station_id}."""
    osm_id_to_id: dict[str, uuid.UUID] = {}

    for feature in stations_geojson["features"]:
        osm_id = feature["properties"]["osm_id"]
        raw_name = feature["properties"]["name"]
        name = STATION_NAME_OVERRIDES.get(raw_name, raw_name)
        lon, lat = feature["geometry"]["coordinates"]
        geom = f"SRID=4326;POINT({lon} {lat})"

        stmt = (
            pg_insert(Stations)
            .values(osm_id=osm_id, name=name, geom=geom)
            .on_conflict_do_update(
                index_elements=[Stations.osm_id],
                set_={"name": name, "geom": geom},
            )
            .returning(Stations.id)
        )
        result = await session.execute(stmt)
        osm_id_to_id[osm_id] = result.scalar_one()

    return osm_id_to_id


async def upsert_lines(
    session: AsyncSession, lines_geojson: dict
) -> dict[str, uuid.UUID]:
    """
    Returns {raw_line_name: line_id} -- keyed by the RAW osm name (not the
    cleaned one) because that's what line_stations.json's `line_name` field
    joins against in upsert_line_stations(). The row actually written to
    the DB uses the cleaned name.

    Skips lines missing from LINE_PERFORMANCE (looked up by cleaned name).
    """
    name_to_id: dict[str, uuid.UUID] = {}

    for feature in lines_geojson["features"]:
        raw_name = feature["properties"]["name"]
        name = LINE_NAME_OVERRIDES.get(raw_name, raw_name)
        coords = feature["geometry"]["coordinates"]

        performance = LINE_PERFORMANCE.get(name)
        if performance is None:
            print(
                f"[warn] no LINE_PERFORMANCE entry for line '{name}' "
                f"(raw: '{raw_name}'), skipping",
                file=sys.stderr,
            )
            continue

        linestring = ", ".join(f"{lon} {lat}" for lon, lat in coords)
        geom = f"SRID=4326;LINESTRING({linestring})"

        stmt = (
            pg_insert(Lines)
            .values(
                name=name,
                geom=geom,
                max_speed_mps=performance["max_speed_mps"],
                max_acceleration_mps2=performance["max_acceleration_mps2"],
            )
            .on_conflict_do_update(
                index_elements=[Lines.name],
                set_={
                    "geom": geom,
                    "max_speed_mps": performance["max_speed_mps"],
                    "max_acceleration_mps2": performance["max_acceleration_mps2"],
                },
            )
            .returning(Lines.id)
        )
        result = await session.execute(stmt)
        name_to_id[raw_name] = result.scalar_one()

    return name_to_id


async def upsert_line_stations(
    session: AsyncSession,
    line_stations: list,
    line_name_to_id: dict[str, uuid.UUID],
    station_osm_id_to_id: dict[str, uuid.UUID],
) -> None:
    for line in line_stations:
        line_id = line_name_to_id.get(line["line_name"])
        if line_id is None:
            continue  # line was skipped above (missing LINE_PERFORMANCE / no geometry)

        for entry in line["stations"]:
            station_id = station_osm_id_to_id.get(entry["station_osm_id"])
            if station_id is None:
                print(
                    f"[warn] station '{entry['station_name']}' "
                    f"({entry['station_osm_id']}) not found, skipping",
                    file=sys.stderr,
                )
                continue

            stmt = (
                pg_insert(LineStations)
                .values(
                    line_id=line_id,
                    station_id=station_id,
                    sequence=entry["sequence"],
                    distance_to_next_m=entry["distance_to_next_m"],
                )
                .on_conflict_do_update(
                    index_elements=[LineStations.line_id, LineStations.station_id],
                    set_={
                        "sequence": entry["sequence"],
                        "distance_to_next_m": entry["distance_to_next_m"],
                    },
                )
            )
            await session.execute(stmt)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--osm-dir",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "osm_data",
        help="Directory with stations.geojson / lines.geojson / line_stations.json "
        "(default: repo-root osm_data/)",
    )
    args = parser.parse_args()

    stations_geojson, lines_geojson, line_stations = load_osm_data(args.osm_dir)

    async with session_maker() as session:
        station_ids = await upsert_stations(session, stations_geojson)
        line_ids = await upsert_lines(session, lines_geojson)
        await upsert_line_stations(session, line_stations, line_ids, station_ids)
        await session.commit()

    print(
        f"[info] seeded {len(station_ids)} stations, {len(line_ids)} lines "
        f"({len(line_ids)}/{len(lines_geojson['features'])} lines had "
        "LINE_PERFORMANCE data)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    asyncio.run(main())
