|repostatus| |ci-status| |license|

.. |repostatus| image:: https://www.repostatus.org/badges/latest/wip.svg
    :target: https://www.repostatus.org/#wip
    :alt: Project Status: WIP — Initial development is in progress, but there
          has not yet been a stable, usable release suitable for the public.

.. |ci-status| image:: https://github.com/jwodder/chesthulhu/actions/workflows/test.yml/badge.svg
    :target: https://github.com/jwodder/chesthulhu/actions/workflows/test.yml
    :alt: CI Status

.. |license| image:: https://img.shields.io/github/license/jwodder/chesthulhu.svg
    :target: https://opensource.org/licenses/MIT
    :alt: MIT License

`GitHub <https://github.com/jwodder/chesthulhu>`_
| `Issues <https://github.com/jwodder/chesthulhu/issues>`_
| `Changelog <https://github.com/jwodder/chesthulhu/blob/main/CHANGELOG.md>`_

``chesthulhu`` is a Python program for examining a Terraria_ world (``.wld``)
file and extracting information about all chests and other containers in the
world and their contents.

.. _Terraria: http://www.terraria.org

``chesthulhu`` is intended to be compatible with ``.wld`` files created by the
most recent version of Terraria (v1.4.5.6 at time of writing) along with some
recent older versions.

Installation
============
``chesthulhu`` requires Python 3.10 or higher.  Just use `pip
<https://pip.pypa.io>`_ for Python 3 (You have pip, right?) to install it::

    python3 -m pip install git+https://github.com/jwodder/chesthulhu

Usage
=====

::

    chesthulhu [<options>] <wld-file>

``chesthulhu`` takes a path to a ``.wld`` file to examine, and it outputs
information on all the chests in that world.

Terraria's ``.wld`` files are stored in a directory that depends on your OS and
whether the files are saved to Steam Cloud:

=======  ====================================================  ====================================================================================
OS       Saved Locally                                         Saved on Steam Cloud
=======  ====================================================  ====================================================================================
Linux    ``~/.local/share/Terraria/Worlds``                    ``~/.local/share/Steam/userdata/$STEAM_USER_ID/105600/remote/worlds``
macOS    ``~/Library/Application Support/Terraria/Worlds``     ``~/Library/Application Support/Steam/userdata/$STEAM_USER_ID/105600/remote/worlds``
Windows  ``%USERPROFILE%\Documents\My Games\Terraria\Worlds``  ``C:\Program Files (x86)\Steam\userdata\%STEAM_USER_ID%\105600\remote\worlds``
=======  ====================================================  ====================================================================================

Options
-------

-o PATH, --outfile PATH         Write the output to the given path.  By
                                default, output is written to standard output.


Output Format
=============

``chesthulhu`` outputs a `TOML <https://toml.io>`_ document with two top-level
keys: ``world`` (a string, the name of the world) and ``chest`` (an array of
tables, each describing a single container).

Each ``chest`` table has the following keys:

- ``tile-coords`` — An inline table containing the keys ``x`` and ``y`` (both
  integers) giving the location of the upper-left corner of the container as
  world tile coordinates

- ``gps-coords`` — An inline table giving the location of the upper-left corner
  of the container using in-game GPS coordinates as reported by the Depth
  Meter, the Compass, and their upgrades.  This table contains the following
  keys:

  - ``long`` — the distance in feet east of the world spawn point; negative
    values are to the west of the spawn point

  - ``lat`` — the distance in feet above the world's surface line; negative
    values are underground

- ``type`` — A string giving the type of container (e.g., "Gold Chest" or
  "Obsidian Dresser").  If the type of container is unknown to ``chesthulhu``,
  the value will instead be an inline table containing the keys ``tile-id``,
  ``u``, and ``v`` (all integers) giving the tile ID and sprite sheet
  coordinates.  If no matching tile could be found in the world file for a
  given chest (which normally shouldn't happen), the ``type`` field will be
  absent.

- ``name`` — A string giving the user-defined custom name of the container, or
  the empty string if it has no custom name

- ``contents`` — An array of inline tables, each describing a nonempty stack of
  items in the container.  Each inline table has the following keys:

  - ``item`` — The name of the item, not including any modifier/prefix.  If the
    type of item is unknown to ``chesthulhu``, the value will instead be an
    inline table containing a single ``id`` field (an integer) giving the item
    ID.

  - ``modifier`` — The item's modifier/prefix as string; if the item doesn't
    have a modifier, this field will not be present.  If the modifier is
    unknown to ``chesthulhu``, the value will instead be an inline table
    containing a single ``id`` field (an integer) giving the modifier ID.

  - ``qty`` — An integer giving the number of items in the stack

An example chest table:

.. code:: toml

    [[chest]]
    tile-coords = { x = 56, y = 875 }
    gps-coords = { long = -6280, lat = -764 }
    type = "Dead Man's Chest"
    name = ""
    contents = [
        { item = "Cloud in a Bottle", modifier = "Jagged", qty = 1 },
        { item = "Dynamite", qty = 1 },
        { item = "Healing Potion", qty = 5 },
        { item = "Featherfall Potion", qty = 2 },
        { item = "Recall Potion", qty = 4 },
        { item = "Gold Coin", qty = 1 },
    ]
