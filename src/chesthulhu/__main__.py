from pathlib import Path
import sys
from .iterchests import iterchests


def main() -> None:
    p = Path(sys.argv[1])
    first = True
    for chest in iterchests(p):
        if first:
            first = False
        else:
            print()
        print(
            f"x={chest.x} y={chest.y} long={chest.long} lat={chest.lat} type={chest.type!r} name={chest.name!r}"
        )
        for it in chest.contents:
            s = "- "
            if it.modifier_id != 0:
                if it.modifier_name is not None:
                    s += it.modifier_name
                else:
                    s += f"[MOD {it.modifier_id}]"
                s += " "
            if it.item_name is not None:
                s += it.item_name
            else:
                s += f"#{it.item_id}"
            if it.qty > 1:
                s += f" × {it.qty}"
            print(s)


if __name__ == "__main__":
    main()
