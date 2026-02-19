from __future__ import annotations
from dataclasses import dataclass
import os
import struct
from typing import IO


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

    def read_string(self) -> str:
        sz = self.read_u8()
        return self.read_exact(sz).decode("latin-1")

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
