"""
Extract chest information from a Terraria .wld file

Visit <https://github.com/jwodder/chesthulhu> for more information.
"""

from __future__ import annotations
from collections import defaultdict
from collections.abc import Iterator
import csv
from dataclasses import dataclass
from enum import Enum
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
from .reader import FieldReader

__version__ = version("chesthulhu")
__author__ = "John Thorvald Wodder II"
__author_email__ = "chesthulhu@varonathe.org"
__license__ = "MIT"
__url__ = "https://github.com/jwodder/chesthulhu"


@dataclass
class WorldOfChests:
    world_name: str
    chests: list[Chest]


@dataclass
class Chest:
    x: int
    y: int
    long: int
    lat: int
    type: str | RawChestType | None
    name: str
    contents: list[ItemStack]


@dataclass
class ItemStack:
    qty: int
    item: str | Id
    modifier: str | Id | None


@dataclass
class Id:
    value: int


@dataclass
class RawChestType:
    tile_id: int
    u: int
    v: int


@dataclass
class Database:
    versions: dict[int, VersionInfo]
    containers: dict[tuple[int, int, int], str]
    items: dict[int, str]
    modifiers: dict[int, str]

    @classmethod
    def load(cls) -> Database:
        data_dir = files("chesthulhu") / "data"
        versions = {}
        with (data_dir / "versions.csv").open(encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                v = int(row["wld_version"])
                coord_jump = int(row["coord_jump"])
                global_slots = row["global_slots"] == "t"
                versions[v] = VersionInfo(
                    coord_jump=coord_jump, global_slots=global_slots
                )
        containers = {}
        with (data_dir / "containers.csv").open(encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                tile_id = int(row["tile_id"])
                u = int(row["u"])
                v = int(row["v"])
                name = row["name"]
                containers[(tile_id, u, v)] = name
        items = {}
        with (data_dir / "items.csv").open(encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                items[int(row["id"])] = row["name"]
        modifiers = {}
        with (data_dir / "modifiers.csv").open(encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            for row in reader:
                modifiers[int(row["id"])] = row["name"]
        return cls(
            versions=versions, containers=containers, items=items, modifiers=modifiers
        )

    def get_version_info(self, version: int) -> VersionInfo:
        raise NotImplementedError

    def get_container_type(self, tile_id: int, u: int, v: int) -> str | RawChestType:
        return self.containers.get(
            (tile_id, u, v), RawChestType(tile_id=tile_id, u=u, v=v)
        )

    def get_item(self, item_id: int) -> str | Id:
        return self.items.get(item_id, Id(item_id))

    def get_modifier(self, mod_id: int) -> str | Id:
        return self.modifiers.get(mod_id, Id(mod_id))


@dataclass
class VersionInfo:
    coord_jump: int
    global_slots: bool


@dataclass
class WorldInfo:
    name: str
    global_slots: bool
    section_offsets: list[int]
    important_tile_ids: set[int]
    tile_height: int
    tile_width: int
    spawn_point_x: int
    underground_level: int

    def tile_coords_to_gps(self, x: int, y: int) -> tuple[int, int]:
        long = (x - self.spawn_point_x) * 2
        lat = (self.underground_level - y) * 2
        return (long, lat)


@dataclass
class Tile:
    x: int
    y: int
    tile_id: int | None
    u: int | None
    v: int | None
    tile_color: int | None
    wall_type: int | None
    wall_color: int | None
    liquid: Liquid | None
    liquid_amount: int | None
    red_wire: bool
    blue_wire: bool
    green_wire: bool
    yellow_wire: bool
    tile_slope: int
    actuator: bool
    actuated: bool
    tile_painted: bool
    wall_painted: bool
    block_echo: bool
    wall_echo: bool
    block_illuminant: bool
    wall_illuminant: bool


class Liquid(Enum):
    WATER = 1
    LAVA = 2
    HONEY = 3


def read_chests(p: Path, db: Database) -> WorldOfChests:
    with FieldReader(p) as reader:
        info = read_world_info(reader, db)
        chests = list(iterchests(reader, info, db))
        x_to_ys = defaultdict(set)
        for c in chests:
            x_to_ys[c.x].add(c.y)
        coords2chest_types: dict[tuple[int, int], str | RawChestType] = {}
        for tile, run_length in itertiles_rle(reader, info):
            if tile.tile_id is not None and tile.u is not None and tile.v is not None:
                for y in x_to_ys[tile.x]:
                    if y in range(tile.y, tile.y + run_length):
                        coords2chest_types[(tile.x, y)] = db.get_container_type(
                            tile.tile_id, tile.u, tile.v
                        )
        for c in chests:
            c.type = coords2chest_types.get((c.x, c.y))
        return WorldOfChests(world_name=info.name, chests=chests)


def read_world_info(reader: FieldReader, db: Database) -> WorldInfo:
    reader.seek(0)
    version = reader.read_i32()
    vi = db.get_version_info(version)
    reader.seek(4 + 7 + 1 + 12)
    section_qty = reader.read_i16()
    section_offsets = [reader.read_i32() for _ in range(section_qty)]
    important_tile_qty = reader.read_i16()
    important_bytes = (important_tile_qty + 7) // 8
    important = set()
    for i in range(important_bytes):
        b = reader.read_u8()
        for j in range(8):
            if b & (1 << j):
                important.add(i * 8 + j)
    world_name = reader.read_string()
    _world_seed = reader.read_string()  # noqa: F841
    _generator_version = reader.read_i64()  # noqa: F841
    _guid = reader.read_exact(16)  # noqa: F841
    _world_id = reader.read_i32()  # noqa: F841
    _bounds = reader.read_rect()  # noqa: F841
    tile_height = reader.read_i32()  # noqa: F841
    tile_width = reader.read_i32()  # noqa: F841
    reader.advance(vi.coord_jump)
    spawn_point_x = reader.read_i32()
    _spawn_point_y = reader.read_i32()  # noqa: F841
    underground_level = reader.read_double()
    return WorldInfo(
        name=world_name,
        global_slots=vi.global_slots,
        section_offsets=section_offsets,
        important_tile_ids=important,
        tile_height=tile_height,
        tile_width=tile_width,
        spawn_point_x=spawn_point_x,
        underground_level=int(underground_level),
    )


def iterchests(reader: FieldReader, info: WorldInfo, db: Database) -> Iterator[Chest]:
    reader.seek(info.section_offsets[2])
    chest_qty = reader.read_i16()
    if info.global_slots:
        slot_qty = reader.read_i16()
    for _ in range(chest_qty):
        x = reader.read_i32()
        y = reader.read_i32()
        long, lat = info.tile_coords_to_gps(x, y)
        name = reader.read_string()
        if not info.global_slots:
            slot_qty = reader.read_i32()
        contents = []
        for _ in range(slot_qty):
            qty = reader.read_i16()
            if qty > 0:
                item_id = reader.read_i32()
                modifier_id = reader.read_u8()
                contents.append(
                    ItemStack(
                        qty=qty,
                        item=db.get_item(item_id),
                        modifier=db.get_modifier(modifier_id),
                    )
                )
        yield Chest(
            x=x,
            y=y,
            long=long,
            lat=lat,
            type=None,
            name=name,
            contents=contents,
        )


def itertiles_rle(reader: FieldReader, info: WorldInfo) -> Iterator[tuple[Tile, int]]:
    reader.seek(info.section_offsets[1])
    y = 0
    x = 0
    while (start := reader.tell()) < info.section_offsets[2]:
        flags = reader.read_u8()  # lihzahrd's flags1
        tile_flags = 0
        flags4 = 0
        tile_id = None
        u = None
        v = None
        tile_color = None
        wall_type = None
        wall_color = None
        if flags & (1 << 0):
            tile_flags = reader.read_u8()  # lihzahrd's flags2
            if tile_flags & (1 << 0):
                tile_flags |= reader.read_u8() << 8  # lihzahrd's flags3
                # Per <https://github.com/Steffo99/lihzahrd/blob
                #   /c162d33a9204164c27643bcbb33035120b0032aa
                #   /src/lihzahrd/world.py#L278-L279>:
                if tile_flags & (1 << 8):
                    flags4 = reader.read_u8()
        if flags & (1 << 1):
            tile_id = reader.read_u8()
            if flags & (1 << 5):
                tile_id |= reader.read_u8() << 8
            if tile_id in info.important_tile_ids:
                u = reader.read_i16()
                v = reader.read_i16()
            if tile_flags & (1 << 11):
                tile_color = reader.read_u8()
        if flags & (1 << 2):
            wall_type = reader.read_u8()
            if tile_flags & (1 << 12):
                wall_color = reader.read_u8()
        match (flags >> 3) & 0b11:
            case 0:
                liquid = None
            case 1:
                liquid = Liquid.WATER
            case 2:
                liquid = Liquid.LAVA
            case 3:
                liquid = Liquid.HONEY
        if liquid is not None:
            liquid_amount = reader.read_u8()
        else:
            liquid_amount = None
        if tile_flags & (1 << 14):
            assert wall_type is not None
            wall_type |= reader.read_u8() << 8
        match (flags >> 6) & 0b11:
            case 0:
                rle_len = 1
            case 1:
                rle_len = reader.read_u8() + 1
            case 2:
                rle_len = reader.read_i16() + 1
            case i:
                raise ValueError(f"unexpected RLE len bits at offset {start:#x}: {i}")
        yield (
            Tile(
                x=x,
                y=y,
                tile_id=tile_id,
                u=u,
                v=v,
                tile_color=tile_color,
                wall_type=wall_type,
                wall_color=wall_color,
                liquid=liquid,
                liquid_amount=liquid_amount,
                red_wire=bool(tile_flags & 0b1),
                blue_wire=bool(tile_flags & 0b10),
                green_wire=bool(tile_flags & 0b100),
                tile_slope=(tile_flags >> 4) & 0b111,
                actuator=bool(tile_flags & (1 << 9)),
                actuated=bool(tile_flags & (1 << 10)),
                tile_painted=bool(tile_flags & (1 << 11)),
                wall_painted=bool(tile_flags & (1 << 12)),
                yellow_wire=bool(tile_flags & (1 << 13)),
                block_echo=bool(flags4 & 1),
                wall_echo=bool(flags4 & (1 << 2)),
                block_illuminant=bool(flags4 & (1 << 3)),
                wall_illuminant=bool(flags4 & (1 << 4)),
            ),
            rle_len,
        )
        y += rle_len
        if y == info.tile_height:
            y = 0
            x += 1
    assert x == info.tile_width, f"{x=} != {info.tile_width=}"
    assert y == 0, f"{y=} != 0"
