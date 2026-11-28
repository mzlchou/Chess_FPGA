"""Checks that the piece hardware fits and the board pads line up.

For every piece type it makes sure:
  - the washer, plug, bolt, nut and magnets fit in their pockets without overlapping the body
  - the magnet pockets and resistor cavity leave a printable wall to the outside
  - all the metal sits on the contact plane and the plastic stays above it
  - nothing on the body sticks out where the claw jaws close around the neck

Then it checks the pad sizes against the contact sizes, so a piece that's up
to PLACEMENT_TOLERANCE off center still reads correctly and never shorts.
Last, it checks that the steel washer under each square fits, stays clear of
the wire holes and lines up with the magnets in the pieces.

Run from robotics/cad:  python checks/fit_check.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from cadgen import build123d as bd  # noqa: E402

from lib import dims  # noqa: E402
from lib import pieces  # noqa: E402
from lib.pieces import center_nut, center_screw, contact_washer, cone, cylinder, make_contact_plug, piece_body, piece_magnets  # noqa: E402

all_passed = True


def check(description: str, passed: bool, detail: str = "") -> None:
    global all_passed
    all_passed &= bool(passed)
    print(f"  {'PASS' if passed else 'FAIL'}  {description}  {detail}")


def overlap(a, b) -> float:
    return (a & b).volume


for kind, (height, _base_diameter) in dims.PIECES.items():
    print(kind)
    body = piece_body(kind)
    hardware = {
        "plug": make_contact_plug(),
        "washer": contact_washer(),
        "bolt": center_screw(),
        "nut": center_nut(),
        "magnets": piece_magnets(),
    }

    for name, part in hardware.items():
        volume = overlap(body, part)
        check(f"{name} fits in the body", volume < 1e-3, f"overlap {volume:.4f} mm3")
    for a, b in (("plug", "washer"), ("plug", "bolt"), ("plug", "nut"), ("magnets", "nut"), ("magnets", "washer")):
        volume = overlap(hardware[a], hardware[b])
        check(f"{a} and {b} don't overlap", volume < 1e-3, f"overlap {volume:.4f} mm3")

    bounds = body.bounding_box()
    check("plastic stays above the contact plane", abs(bounds.min.Z - dims.METAL_PROUD) < 1e-6, f"lowest plastic at z = {bounds.min.Z:.2f}")
    check("piece is the right height", abs(bounds.max.Z - height) < 1e-6, f"{bounds.max.Z:.1f} mm")
    for name in ("washer", "bolt", "plug"):
        z = hardware[name].bounding_box().min.Z
        check(f"{name} sits on the contact plane", abs(z) < 1e-6, f"z = {z:.2f}")

    # The jaws close in this band, so the body has to stay inside the neck radius here.
    band_bottom, band_top = height - dims.HEAD_HEIGHT, height - dims.CAP_HEIGHT
    outside_the_neck = cylinder(40, band_bottom, band_top) - cylinder(dims.NECK_RADIUS + 0.01, band_bottom - 1, band_top + 1)
    volume = overlap(body, outside_the_neck)
    check("nothing sticks out where the claw closes", volume < 1e-3, f"{volume:.4f} mm3")

    # Grow the closed pockets by a printable wall and make sure they still fit inside the piece.
    wall = 0.8
    outside = pieces.foot(_base_diameter / 2) + pieces.MIDDLES[kind](height) + pieces.head(height)
    grown_magnets = cylinder(pieces.MAGNET_POCKET_RADIUS + wall, pieces.MAGNET_BOTTOM, pieces.MAGNET_POCKET_TOP + wall)
    grown_magnets = bd.Pos(0, pieces.MAGNET_Y, 0) * grown_magnets + bd.Pos(0, -pieces.MAGNET_Y, 0) * grown_magnets
    volume = (grown_magnets - outside).volume
    check(f"at least {wall} mm of wall around the magnets", volume < 1e-3, f"{volume:.4f} mm3 pokes out")
    radius = dims.RESISTOR_CAVITY_RADIUS + wall
    grown_cavity = cylinder(radius, pieces.CAVITY_BOTTOM, pieces.CAVITY_TOP) + cone(radius, 0.0, pieces.CAVITY_TOP, pieces.CAVITY_TOP + radius)
    volume = (grown_cavity - outside).volume
    check(f"at least {wall} mm of wall around the resistor cavity", volume < 1e-3, f"{volume:.4f} mm3 pokes out")

    grams = body.volume / 1000 * 1.24  # PLA is about 1.24 g/cm3
    print(f"  body is {body.volume / 1000:.1f} cm3, about {grams:.0f} g of PLA at 100% infill")

# Board pads. Think of the piece sliding off center by up to the tolerance in any direction.
# The bolt head is a hexagon, so use its smallest radius for "still touches"
# and its biggest for "never touches".
head_inner = dims.M3_HEAD_FLATS / 2
head_outer = dims.M3_HEAD_CORNERS / 2
tolerance = dims.PLACEMENT_TOLERANCE
print(f"board pads, piece up to {tolerance:.1f} mm off center")
check(
    "center pad still touches the bolt head",
    dims.PAD_CENTER_RADIUS + head_inner > tolerance,
    f"margin {dims.PAD_CENTER_RADIUS + head_inner - tolerance:.2f} mm",
)
check(
    "center pad never touches the washer",
    dims.PAD_CENTER_RADIUS + tolerance < dims.WASHER_ID / 2,
    f"margin {dims.WASHER_ID / 2 - dims.PAD_CENTER_RADIUS - tolerance:.2f} mm",
)
check(
    "ring pad never touches the bolt head",
    dims.PAD_RING_INNER > head_outer + tolerance,
    f"margin {dims.PAD_RING_INNER - head_outer - tolerance:.2f} mm",
)
check(
    "ring pad still touches the washer",
    dims.PAD_RING_INNER < dims.WASHER_OD / 2 - tolerance,
    f"margin {dims.WASHER_OD / 2 - tolerance - dims.PAD_RING_INNER:.2f} mm",
)

# Steel washer under each square, and how it lines up with the piece magnets.
from board.tile_2x2 import PLATE_THICKNESS, RING_WIRE_HOLE_X, TARGET_POCKET_RADIUS, WIRE_HOLE_DIA  # noqa: E402

print("steel washer under each square")
check(
    "washer fits in the plate",
    dims.TARGET_WASHER_THICKNESS <= PLATE_THICKNESS - dims.TARGET_SKIN,
    f"{PLATE_THICKNESS - dims.TARGET_SKIN:.1f} mm of room for a {dims.TARGET_WASHER_THICKNESS:.1f} mm washer",
)
check("skin over the washer is printable", dims.TARGET_SKIN >= 0.6, f"{dims.TARGET_SKIN:.1f} mm")
check(
    "center wire comes up through the washer's hole",
    WIRE_HOLE_DIA / 2 + 1.0 < dims.TARGET_WASHER_ID / 2,
    f"{dims.TARGET_WASHER_ID / 2 - WIRE_HOLE_DIA / 2:.2f} mm to spare",
)
check(
    "ring wire hole misses the washer pocket",
    RING_WIRE_HOLE_X - WIRE_HOLE_DIA / 2 - TARGET_POCKET_RADIUS >= 0.8,
    f"{RING_WIRE_HOLE_X - WIRE_HOLE_DIA / 2 - TARGET_POCKET_RADIUS:.2f} mm wall",
)
check(
    "ring wire hole is inside the ring pad",
    dims.PAD_RING_INNER < RING_WIRE_HOLE_X - WIRE_HOLE_DIA / 2 and RING_WIRE_HOLE_X + WIRE_HOLE_DIA / 2 < dims.PAD_RING_OUTER,
    f"hole at r {RING_WIRE_HOLE_X:.2f}",
)
magnet_inner = pieces.MAGNET_Y - dims.PIECE_MAGNET_DIA / 2
magnet_outer = pieces.MAGNET_Y + dims.PIECE_MAGNET_DIA / 2
check(
    "piece magnets sit over the steel washer",
    magnet_inner < dims.TARGET_WASHER_OD / 2 and magnet_outer > dims.TARGET_WASHER_ID / 2,
    f"magnets cover r {magnet_inner:.1f} to {magnet_outer:.1f}, washer is r {dims.TARGET_WASHER_ID / 2:.1f} to {dims.TARGET_WASHER_OD / 2:.1f}",
)
gap = pieces.MAGNET_BOTTOM + dims.TARGET_SKIN
print(f"  air and plastic between the magnets and the steel washer: {gap:.2f} mm")
print(f"  print pause for the magnets: {pieces.MAGNET_POCKET_TOP - dims.METAL_PROUD:.2f} mm up from the bed")

sys.exit(0 if all_passed else 1)
