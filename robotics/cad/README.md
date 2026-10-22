# Robotics CAD

This folder has the 3D models for the chess robot: the pieces, the claw that picks them up, and a small test chunk of the board. Everything is Python ([build123d](https://build123d.readthedocs.io)), built with `cadgen` from the text-to-cad plugin. Basically its just code -> CAD.

All the sizes are in one file, `src/lib/dims.py`

## setup

You need [uv](https://docs.astral.sh/uv/). From `robotics/cad/`:

```bash
PY="uvx --no-config --managed-python --python 3.13 --from cadgen==0.7.26 python"
$PY build.py                # everything
$PY build.py claw           # just one folder
$PY build.py pieces/pawn.py # just one file
```

might be different depending on ur env and setup

## dir

```
src/
  lib/       shared code: dims.py has every size, pieces.py, claw.py and gears.py make the shapes
  pieces/    the six pieces, the contact plug, and piece_lineup (all six in a row, for looking at)
  claw/      jaw, pinion, housing, and claw_assembly (the claw holding a pawn, for looking at)
  board/     tile_2x2, four squares for testing piece detection
checks/      fit_check.py and claw_check.py
build.py     builds everything in src/
STEP/        exact CAD files, same folders as src/
STL/         meshes for the slicer, same folders as src/
tmp/         rendered pictures (not committed)
```

Every model makes a STEP file

## What we need based on this design

For each piece:


| Qty | Part                                | What it's for                                                              |
| --- | ----------------------------------- | -------------------------------------------------------------------------- |
| 1   | M12 flat washer, DIN 125 (24 mm OD) | The outer contact, and some extra weight                                   |
| 1   | M3 x 8 countersunk screw            | The center contact                                                         |
| 1   | M3 nut                              | Holds one resistor lead against the screw                                  |
| 1   | 1/4 W, 1% resistor                  | Tells the board which piece this is. Values are in the piece detection doc |


For the claw:


| Qty | Part                                                        |
| --- | ----------------------------------------------------------- |
| 1   | MG90S micro servo. It comes with horns and screws           |
| 4   | M3 heat-set inserts, for bolting the claw to the Z carriage |


