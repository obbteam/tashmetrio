from typing import Any, Optional
import datetime
import decimal
import enum
import uuid

from geoalchemy2.types import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    Time,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DirectionType(str, enum.Enum):
    FORWARD = "FORWARD"
    BACKWARD = "BACKWARD"


class TripStatusType(str, enum.Enum):
    ON_TIME = "ON TIME"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"


t_geography_columns = Table(
    "geography_columns",
    Base.metadata,
    Column("f_table_catalog", String),
    Column("f_table_schema", String),
    Column("f_table_name", String),
    Column("f_geography_column", String),
    Column("coord_dimension", Integer),
    Column("srid", Integer),
    Column("type", Text),
)


t_geometry_columns = Table(
    "geometry_columns",
    Base.metadata,
    Column("f_table_catalog", String(256, "C")),
    Column("f_table_schema", String),
    Column("f_table_name", String),
    Column("f_geometry_column", String),
    Column("coord_dimension", Integer),
    Column("srid", Integer),
    Column("type", String(30)),
)


class GooseDbVersion(Base):
    __tablename__ = "goose_db_version"
    __table_args__ = (PrimaryKeyConstraint("id", name="goose_db_version_pkey"),)

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(
            start=1, increment=1, minvalue=1, maxvalue=2147483647, cycle=False, cache=1
        ),
        primary_key=True,
        autoincrement=True,
    )
    version_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_applied: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tstamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )


class Lines(Base):
    __tablename__ = "lines"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="lines_pkey"),
        UniqueConstraint("name", name="lines_name_key"),
        Index("idx_lines_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    geom: Mapped[Any] = mapped_column(
        Geometry(
            "LINESTRING",
            4326,
            2,
            from_text="ST_GeomFromEWKT",
            name="geometry",
            nullable=False,
        ),
        nullable=False,
    )
    max_speed_mps: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )
    max_acceleration_mps2: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 2), nullable=False
    )

    incidents: Mapped[list["Incidents"]] = relationship(
        "Incidents", back_populates="line"
    )
    line_stations: Mapped[list["LineStations"]] = relationship(
        "LineStations", back_populates="line"
    )
    trains: Mapped[list["Trains"]] = relationship("Trains", back_populates="line")
    trips: Mapped[list["Trips"]] = relationship("Trips", back_populates="line")


class SpatialRefSys(Base):
    __tablename__ = "spatial_ref_sys"
    __table_args__ = (
        CheckConstraint(
            "srid > 0 AND srid <= 998999", name="spatial_ref_sys_srid_check"
        ),
        PrimaryKeyConstraint("srid", name="spatial_ref_sys_pkey"),
    )

    srid: Mapped[int] = mapped_column(Integer, primary_key=True)
    auth_name: Mapped[Optional[str]] = mapped_column(String(256))
    auth_srid: Mapped[Optional[int]] = mapped_column(Integer)
    srtext: Mapped[Optional[str]] = mapped_column(String(2048))
    proj4text: Mapped[Optional[str]] = mapped_column(String(2048))


class Stations(Base):
    __tablename__ = "stations"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="stations_pkey"),
        UniqueConstraint("name", name="stations_name_key"),
        UniqueConstraint("osm_id", name="stations_osm_id_key"),
        Index("idx_stations_geom", "geom", postgresql_using="gist"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    osm_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    geom: Mapped[Any] = mapped_column(
        Geometry(
            "POINT",
            4326,
            2,
            from_text="ST_GeomFromEWKT",
            name="geometry",
            nullable=False,
        ),
        nullable=False,
    )

    incidents: Mapped[list["Incidents"]] = relationship(
        "Incidents", back_populates="station"
    )
    line_stations: Mapped[list["LineStations"]] = relationship(
        "LineStations", back_populates="station"
    )
    transfers_station_a: Mapped[list["Transfers"]] = relationship(
        "Transfers", foreign_keys="[Transfers.station_a_id]", back_populates="station_a"
    )
    transfers_station_b: Mapped[list["Transfers"]] = relationship(
        "Transfers", foreign_keys="[Transfers.station_b_id]", back_populates="station_b"
    )


class Incidents(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "line_id IS NOT NULL OR station_id IS NOT NULL",
            name="line_or_station_not_null",
        ),
        ForeignKeyConstraint(
            ["line_id"], ["lines.id"], ondelete="CASCADE", name="incidents_line_id_fkey"
        ),
        ForeignKeyConstraint(
            ["station_id"],
            ["stations.id"],
            ondelete="CASCADE",
            name="incidents_station_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="incidents_pkey"),
        Index("idx_incidents_line_id", "line_id"),
        Index("idx_incidents_station_id", "station_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), nullable=False, server_default=text("now()")
    )
    line_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    station_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    ended_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    line: Mapped[Optional["Lines"]] = relationship("Lines", back_populates="incidents")
    station: Mapped[Optional["Stations"]] = relationship(
        "Stations", back_populates="incidents"
    )


class LineStations(Base):
    __tablename__ = "line_stations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["line_id"],
            ["lines.id"],
            ondelete="CASCADE",
            name="line_stations_line_id_fkey",
        ),
        ForeignKeyConstraint(
            ["station_id"],
            ["stations.id"],
            ondelete="CASCADE",
            name="line_stations_station_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="line_stations_pkey"),
        UniqueConstraint(
            "line_id", "sequence", name="line_stations_line_id_sequence_key"
        ),
        UniqueConstraint(
            "line_id", "station_id", name="line_stations_line_id_station_id_key"
        ),
        Index("idx_line_stations_line_id", "line_id"),
        Index("idx_line_stations_station_id", "station_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    line_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    station_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    distance_to_next_m: Mapped[Optional[int]] = mapped_column(Integer)

    line: Mapped["Lines"] = relationship("Lines", back_populates="line_stations")
    station: Mapped["Stations"] = relationship(
        "Stations", back_populates="line_stations"
    )
    trips: Mapped[list["Trips"]] = relationship(
        "Trips", back_populates="current_segment"
    )


class Trains(Base):
    __tablename__ = "trains"
    __table_args__ = (
        ForeignKeyConstraint(
            ["line_id"], ["lines.id"], ondelete="CASCADE", name="trains_line_id_fkey"
        ),
        PrimaryKeyConstraint("id", name="trains_pkey"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    line_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), nullable=False, server_default=text("now()")
    )

    line: Mapped["Lines"] = relationship("Lines", back_populates="trains")
    timetable_entries: Mapped[list["TimetableEntries"]] = relationship(
        "TimetableEntries", back_populates="train"
    )
    trips: Mapped[list["Trips"]] = relationship("Trips", back_populates="train")


class Transfers(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint(
            "station_a_id < station_b_id", name="tranfers_pair_should_be_single"
        ),
        ForeignKeyConstraint(
            ["station_a_id"],
            ["stations.id"],
            ondelete="CASCADE",
            name="transfers_station_a_id_fkey",
        ),
        ForeignKeyConstraint(
            ["station_b_id"],
            ["stations.id"],
            ondelete="CASCADE",
            name="transfers_station_b_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="transfers_pkey"),
        UniqueConstraint(
            "station_a_id",
            "station_b_id",
            name="transfers_station_a_id_station_b_id_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    station_a_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    station_b_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    walk_time_s: Mapped[int] = mapped_column(Integer, nullable=False)

    station_a: Mapped["Stations"] = relationship(
        "Stations", foreign_keys=[station_a_id], back_populates="transfers_station_a"
    )
    station_b: Mapped["Stations"] = relationship(
        "Stations", foreign_keys=[station_b_id], back_populates="transfers_station_b"
    )


class TimetableEntries(Base):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["train_id"],
            ["trains.id"],
            ondelete="CASCADE",
            name="timetable_entries_train_id_fkey",
        ),
        PrimaryKeyConstraint("id", name="timetable_entries_pkey"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    train_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    direction: Mapped[DirectionType] = mapped_column(
        Enum(
            DirectionType,
            values_callable=lambda cls: [member.value for member in cls],
            name="direction_type",
        ),
        nullable=False,
    )
    departure_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)

    train: Mapped["Trains"] = relationship("Trains", back_populates="timetable_entries")
    trips: Mapped[list["Trips"]] = relationship(
        "Trips", back_populates="timetable_entry"
    )


class Trips(Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint(
            "progress_pct >= 0::numeric AND progress_pct <= 100::numeric",
            name="trips_progress_pct_check",
        ),
        ForeignKeyConstraint(
            ["current_segment_id"],
            ["line_stations.id"],
            ondelete="SET NULL",
            name="trips_current_segment_id_fkey",
        ),
        ForeignKeyConstraint(["line_id"], ["lines.id"], name="trips_line_id_fkey"),
        ForeignKeyConstraint(
            ["timetable_entry_id"],
            ["timetable_entries.id"],
            ondelete="CASCADE",
            name="trips_timetable_entry_id_fkey",
        ),
        ForeignKeyConstraint(
            ["train_id"], ["trains.id"], ondelete="CASCADE", name="trips_train_id_fkey"
        ),
        PrimaryKeyConstraint("id", name="trips_pkey"),
        Index(
            "idx_trips_current_position", "current_position", postgresql_using="gist"
        ),
        Index("idx_trips_current_segment_id", "current_segment_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("uuid_generate_v4()")
    )
    train_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    timetable_entry_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    departure_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), nullable=False
    )
    estimated_arrival_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), nullable=False
    )
    trip_status: Mapped[TripStatusType] = mapped_column(
        Enum(
            TripStatusType,
            values_callable=lambda cls: [member.value for member in cls],
            name="trip_status_type",
        ),
        nullable=False,
    )
    progress_pct: Mapped[decimal.Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, server_default=text("0")
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), nullable=False, server_default=text("now()")
    )
    is_finished: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    line_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    current_segment_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(True), nullable=False, server_default=text("now()")
    )
    current_segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    current_position: Mapped[Optional[Any]] = mapped_column(
        Geometry("POINT", 4326, 2, from_text="ST_GeomFromEWKT", name="geometry")
    )

    current_segment: Mapped[Optional["LineStations"]] = relationship(
        "LineStations", back_populates="trips"
    )
    line: Mapped["Lines"] = relationship("Lines", back_populates="trips")
    timetable_entry: Mapped["TimetableEntries"] = relationship(
        "TimetableEntries", back_populates="trips"
    )
    train: Mapped["Trains"] = relationship("Trains", back_populates="trips")
