from __future__ import annotations
import argparse
from pathlib import Path
import sys
from . import Database, Id, __version__, read_chests


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--outfile", default="-")
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("infile", type=Path)
    args = parser.parse_args()
    db = Database.load()
    data = read_chests(args.infile, db)
    if args.outfile == "-":
        outfp = sys.stdout
    else:
        outfp = open(args.outfile, "w", encoding="utf-8")
    with outfp:
        first = True
        for chest in data.chests:
            if first:
                first = False
            else:
                print(file=outfp)
            print(
                f"x={chest.x} y={chest.y} long={chest.long} lat={chest.lat}"
                f" type={chest.type!r} name={chest.name!r}",
                file=outfp,
            )
            for it in chest.contents:
                s = "- "
                if it.modifier is not None:
                    if isinstance(it.modifier, str):
                        s += it.modifier
                    elif isinstance(it.modifier, Id):
                        s += f"[MOD {it.modifier}]"
                    s += " "
                if isinstance(it.item, str):
                    s += it.item
                else:
                    s += f"#{it.item}"
                if it.qty > 1:
                    s += f" × {it.qty}"
                print(s, file=outfp)


if __name__ == "__main__":
    main()
