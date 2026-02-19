#!/usr/bin/env python3
from __future__ import annotations
from collections.abc import Iterator
import csv
from dataclasses import asdict, dataclass, fields, replace
from enum import Enum
import os
from pathlib import Path
import struct
import sys
from typing import IO

# Mapping from .wld versions to the number of bytes in (world width in tiles,
# span point x]
COORD_JUMPS = {
    279: 89,
    316: 98,
    317: 98,
    318: 98,
}


class Liquid(Enum):
    WATER = 1
    LAVA = 2
    HONEY = 3


@dataclass
class Tile:
    x: int
    y: int
    long: int
    lat: int
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

    def for_csv(self) -> dict[str, int | str]:
        d = asdict(self)
        for k, v in d.items():
            if v is True:
                d[k] = "t"
            elif v is False:
                d[k] = "f"
            elif isinstance(v, Liquid):
                d[k] = v.name.lower()
        return d


def itertiles(p: Path) -> Iterator[Tile]:
    for tile, run_length in itertiles_rle(p):
        for i in range(run_length):
            yield replace(tile, y=tile.y + i, lat=tile.lat - 2 * i)


def itertiles_rle(p: Path) -> Iterator[tuple[Tile, int]]:
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
        tile_height = reader.read_i32()
        tile_width = reader.read_i32()
        reader.advance(COORD_JUMPS[version])
        spawn_point_x = reader.read_i32()
        _spawn_point_y = reader.read_i32()
        underground_level = int(reader.read_double())
        reader.seek(section_offsets[1])
        y = 0
        x = 0
        while (start := reader.tell()) < section_offsets[2]:
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
                    # Per <https://github.com/Steffo99/lihzahrd/blob/c162d33a9204164c27643bcbb33035120b0032aa/src/lihzahrd/world.py#L278-L279>:
                    if tile_flags & (1 << 8):
                        flags4 = reader.read_u8()
            if flags & (1 << 1):
                tile_id = reader.read_u8()
                if flags & (1 << 5):
                    tile_id |= reader.read_u8() << 8
                if tile_id in important:
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
                    raise ValueError(
                        f"unexpected RLE len bits at offset {start:#x}: {i}"
                    )
            yield (
                Tile(
                    x=x,
                    y=y,
                    lat=(underground_level - y) * 2,
                    long=(x - spawn_point_x) * 2,
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
            if y == tile_height:
                y = 0
                x += 1
        assert x == tile_width, f"{x=} != {tile_width=}"
        assert y == 0, f"{y=} != 0"


@dataclass
class ByteReader:
    fp: IO[bytes]

    def seek(self, pos: int) -> None:
        self.fp.seek(pos)

    def advance(self, length: int) -> None:
        self.fp.seek(length, os.SEEK_CUR)

    def tell(self) -> int:
        return self.fp.tell()

    def read_exact(self, length: int) -> bytes:
        bs = self.fp.read(length)
        if len(bs) < length:
            raise ValueError(f"tried to read {length} bytes, got {len(bs)}")
        return bs

    def read_bool(self) -> bool:
        return bool(self.read_u8())

    def read_u8(self) -> int:
        bs = self.read_exact(1)
        return int.from_bytes(bs)  # Not signed

    def read_int(self, length: int) -> int:
        bs = self.read_exact(length)
        return int.from_bytes(bs, byteorder="little", signed=True)

    def read_i16(self) -> int:
        return self.read_int(2)

    def read_i32(self) -> int:
        return self.read_int(4)

    def read_i64(self) -> int:
        return self.read_int(8)

    def read_double(self) -> float:
        bs = self.read_exact(8)
        return struct.unpack("<d", bs)[0]  # type: ignore

    def read_string(self) -> bytes:
        sz = self.read_u8()
        return self.read_exact(sz)

    def read_rect(self) -> Rect:
        left = self.read_i32()
        right = self.read_i32()
        top = self.read_i32()
        bottom = self.read_i32()
        return Rect(left, right, top, bottom)


@dataclass
class Rect:
    left: int
    right: int
    top: int
    bottom: int


if __name__ == "__main__":
    p = Path(sys.argv[1])
    out = csv.DictWriter(sys.stdout, [f.name for f in fields(Tile)])
    out.writeheader()
    for t in itertiles(p):
        out.writerow(t.for_csv())
