from __future__ import annotations
import argparse
from pathlib import Path
import sys
from . import Database, __version__, read_chests, toml_string


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract chest information from a Terraria .wld file\n"
            "\n"
            "Visit <https://github.com/jwodder/chesthulhu> for more information."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-o",
        "--outfile",
        default="-",
        help="Write output to given file [default: stdout]",
    )
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
        print(f"world = {toml_string(data.world_name)}", file=outfp)
        for chest in data.chests:
            print(file=outfp)
            print("[[chest]]", file=outfp)
            print(chest.to_toml(), end="", file=outfp)


if __name__ == "__main__":
    main()
