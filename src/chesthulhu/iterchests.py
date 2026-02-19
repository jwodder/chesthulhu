#!/usr/bin/env python3
from __future__ import annotations
from collections.abc import Iterator
import csv
from dataclasses import asdict, dataclass, fields
from enum import Enum
from importlib.resources import files
from pathlib import Path
from .itertiles import itertiles_rle
from .reader import ByteReader

# Mapping from .wld versions to the number of bytes in (world width in tiles,
# span point x]
COORD_JUMPS = {
    279: 89,
    316: 98,
    317: 98,
    318: 98,
}

CONTAINERS = {
    21: {
        0: "Chest",
        36: "Gold Chest",
        72: "Locked Gold Chest",
        108: "Shadow Chest",
        144: "Locked Shadow Chest",
        180: "Barrel",
        216: "Trash Can",
        252: "Ebonwood Chest",
        288: "Rich Mahogany Chest",
        324: "Pearlwood Chest",
        360: "Ivy Chest",
        396: "Ice Chest",
        432: "Living Wood Chest",
        468: "Skyware Chest",
        504: "Shadewood Chest",
        540: "Web Covered Chest",
        576: "Lihzahrd Chest",
        612: "Water Chest",
        648: "Jungle Chest",
        684: "Corruption Chest",
        720: "Crimson Chest",
        756: "Hallowed Chest",
        792: "Frozen Chest",
        828: "Locked Jungle Chest",
        864: "Locked Corruption Chest",
        900: "Locked Crimson Chest",
        936: "Locked Hallowed Chest",
        972: "Locked Frozen Chest",
        1008: "Dynasty Chest",
        1044: "Honey Chest",
        1080: "Steampunk Chest",
        1116: "Palm Wood Chest",
        1152: "Mushroom Chest",
        1188: "Boreal Wood Chest",
        1224: "Slime Chest",
        1260: "Green Dungeon Chest",
        1296: "Locked Green Dungeon Chest",
        1332: "Pink Dungeon Chest",
        1368: "Locked Pink Dungeon Chest",
        1404: "Blue Dungeon Chest",
        1440: "Locked Blue Dungeon Chest",
        1476: "Bone Chest",
        1512: "Cactus Chest",
        1548: "Flesh Chest",
        1584: "Obsidian Chest",
        1620: "Pumpkin Chest",
        1656: "Spooky Chest",
        1692: "Glass Chest",
        1728: "Martian Chest",
        1764: "Meteorite Chest",
        1800: "Granite Chest",
        1836: "Marble Chest",
    },
    88: {
        0: "Dresser",
        54: "Ebonwood Dresser",
        108: "Rich Mahogany Dresser",
        162: "Pearlwood Dresser",
        216: "Shadewood Dresser",
        270: "Blue Dungeon Dresser",
        324: "Green Dungeon Dresser",
        378: "Pink Dungeon Dresser",
        432: "Golden Dresser",
        486: "Obsidian Dresser",
        540: "Bone Dresser",
        594: "Cactus Dresser",
        648: "Spooky Dresser",
        702: "Skyware Dresser",
        756: "Honey Dresser",
        810: "Lihzahrd Dresser",
        864: "Palm Wood Dresser",
        918: "Mushroom Dresser",
        972: "Boreal Wood Dresser",
        1026: "Slime Dresser",
        1080: "Pumpkin Dresser",
        1134: "Steampunk Dresser",
        1188: "Glass Dresser",
        1242: "Flesh Dresser",
        1296: "Martian Dresser",
        1350: "Meteorite Dresser",
        1404: "Granite Dresser",
        1458: "Marble Dresser",
        1512: "Crystal Dresser",
        1566: "Dynasty Dresser",
        1620: "Frozen Dresser",
        1674: "Living Wood Dresser",
    },
    467: {
        0: "Crystal Chest",
        36: "Golden Chest",
        72: "Spider Chest",
        108: "Lesion Chest",
        144: "Dead Man's Chest",
        180: "Solar Chest",
        216: "Vortex Chest",
        252: "Nebula Chest",
        288: "Stardust Chest",
        324: "Golf Chest",
        360: "Sandstone Chest",
        396: "Bamboo Chest",
        432: "Locked Desert Chest",
        468: "Desert Chest",
    },
}


@dataclass
class Chest:
    x: int
    y: int
    long: int
    lat: int
    type: str | None
    name: str
    contents: list[ItemStack]


@dataclass
class ItemStack:
    qty: int
    item_id: int
    item_name: str | None
    modifier_id: int
    modifier_name: str | None


def iterchests(p: Path) -> Iterator[Chest]:
    with (files("chesthulhu") / "data" / "items.csv").open(
        encoding="utf-8", newline=""
    ) as fp:
        incsv = csv.DictReader(fp)
        items = {int(row["id"]): row["name"] for row in incsv}
    with (files("chesthulhu") / "data" / "prefixes.csv").open(
        encoding="utf-8", newline=""
    ) as fp:
        incsv = csv.DictReader(fp)
        prefixes = {int(row["id"]): row["name"] for row in incsv}
    chest_types = {}
    for t, run_length in itertiles_rle(p):
        if t.v == 0 and (ct := CONTAINERS.get(t.tile_id, {}).get(t.u)) is not None:
            assert run_length == 1
            chest_types[(t.x, t.y)] = ct
    with p.open("rb") as fp:
        reader = ByteReader(fp)
        version = reader.read_i32()
        if version not in COORD_JUMPS:
            raise ValueError(f"Unsupported .wld version: {version}")
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
        _world_name = reader.read_string()
        _world_seed = reader.read_string()
        _generator_version = reader.read_i64()
        _guid = reader.read_exact(16)
        _world_id = reader.read_i32()
        _bounds = reader.read_rect()
        _tile_height = reader.read_i32()
        _tile_width = reader.read_i32()
        reader.advance(COORD_JUMPS[version])
        spawn_point_x = reader.read_i32()
        _spawn_point_y = reader.read_i32()
        underground_level = int(reader.read_double())
        reader.seek(section_offsets[2])
        chest_qty = reader.read_i16()
        for _ in range(chest_qty):
            x = reader.read_i32()
            y = reader.read_i32()
            long = (x - spawn_point_x) * 2
            lat = (underground_level - y) * 2
            name = reader.read_string()
            slot_qty = reader.read_i32()
            contents = []
            for _ in range(slot_qty):
                qty = reader.read_i16()
                if qty > 0:
                    item_id = reader.read_i32()
                    modifier = reader.read_u8()
                    contents.append(
                        ItemStack(
                            qty=qty,
                            item_id=item_id,
                            item_name=items.get(item_id),
                            modifier_id=modifier,
                            modifier_name=prefixes.get(modifier),
                        )
                    )
            yield Chest(
                x=x,
                y=y,
                long=long,
                lat=lat,
                type=chest_types.get((x, y)),
                name=name,
                contents=contents,
            )
