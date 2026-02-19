Data File Formats
=================

The data files read by `chesthulhu` are all comma-separated values (CSV) files
compatible with Python's `csv` module.  All files have header rows and thus
should be read using `csv.DictReader`.

`containers.csv`
----------------

This file contains the information needed to identify the type of a container
from an entry in the tile data section of a `.wld` file.  The columns are:

- `tile_id` (integer) — tile ID
- `u` (integer) — the `u` coordinate of the upper-left tile of the container in
  the tile's sprite sheet
- `v` (integer) — the `v` coordinate of the upper-left tile of the container in
  the tile's sprite sheet
- `name` (string) — the name of the container type

`items.csv`
-----------

This file lists all items in Terraria.  The columns are:

- `id` (integer) — item ID
- `name` (string) — item name

`modifiers.csv`
---------------

This file lists the modifiers/prefixes that can be applied to items.  The
columns are:

- `id` (integer) — modifier ID
- `name` (string) — modifier name

Note that there are some instances of distinct modifiers having the same name;
no attempt is made here to disambiguate them.

`versions.csv`
--------------

This file lists `.wld` file versions supported by `chesthulhu` alongside
necessary version-specific file format information.  The columns are:

- `wld_version` (integer) — the version value from the start of a Terraria
  `.wld` file
- `game_version` (string) — the corresponding Terraria version; this is only
  for readability of the data file and is ignored by `chesthulhu`
- `coord_jump` (integer) — the number of bytes in section 1 of a world file
  with this version between the width of the world in tiles and the
  x-coordinate of the world's spawn point
- `global_slots` — If this is `t`, then a world file with this version stores
  the number of slots per chest a single time near the start of section 2; if
  this is `f`, then each chest entry in section 2 instead stores its own number
  of slots.
