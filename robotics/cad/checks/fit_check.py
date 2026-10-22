"""Checks that the piece hardware fits and the board pads line up.

For every piece type it makes sure:
  - the washer, plug, screw and nut fit in their pockets without overlapping the body
  - all the metal sits on the contact plane and the plastic stays above it
  - nothing on the body sticks out where the claw jaws close around the neck

Then it checks the pad sizes against the contact sizes, so a piece that's up
to PLACEMENT_TOLERANCE off center still reads correctly and never shorts.

Run from robotics/cad:  python checks/fit_check.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from lib import dims  # noqa: E402
from lib.pieces import center_nut, center_screw, contact_washer, cylinder, make_contact_plug, piece_body  # noqa: E402

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
    hardware = {"plug": make_contact_plug(), "washer": contact_washer(), "screw": center_screw(), "nut": center_nut()}

    for name, part in hardware.items():
        volume = overlap(body, part)
        check(f"{name} fits in the body", volume < 1e-3, f"overlap {volume:.4f} mm3")
    volume = overlap(hardware["plug"], hardware["washer"])
    check("plug fits in the washer", volume < 1e-3, f"overlap {volume:.4f} mm3")

    bounds = body.bounding_box()
    check("plastic stays above the contact plane", abs(bounds.min.Z - dims.METAL_PROUD) < 1e-6, f"lowest plastic at z = {bounds.min.Z:.2f}")
    check("piece is the right height", abs(bounds.max.Z - height) < 1e-6, f"{bounds.max.Z:.1f} mm")
    for name in ("washer", "screw", "plug"):
        z = hardware[name].bounding_box().min.Z
        check(f"{name} sits on the contact plane", abs(z) < 1e-6, f"z = {z:.2f}")

    # The jaws close in this band, so the body has to stay inside the neck radius here.
    band_bottom, band_top = height - dims.HEAD_HEIGHT, height - dims.CAP_HEIGHT
    outside_the_neck = cylinder(40, band_bottom, band_top) - cylinder(dims.NECK_RADIUS + 0.01, band_bottom - 1, band_top + 1)
    volume = overlap(body, outside_the_neck)
    check("nothing sticks out where the claw closes", volume < 1e-3, f"{volume:.4f} mm3")

    grams = body.volume / 1000 * 1.24  # PLA is about 1.24 g/cm3
    print(f"  body is {body.volume / 1000:.1f} cm3, about {grams:.0f} g of PLA at 100% infill")

# Board pads. Think of the piece sliding off center by up to the tolerance in any direction.
screw_head_radius = dims.M3_COUNTERSINK_DIA / 2
tolerance = dims.PLACEMENT_TOLERANCE
print(f"board pads, piece up to {tolerance:.1f} mm off center")
check("center pad still touches the screw head", dims.PAD_CENTER_RADIUS + screw_head_radius > tolerance)
check(
    "center pad never touches the washer",
    dims.PAD_CENTER_RADIUS + tolerance < dims.WASHER_ID / 2,
    f"margin {dims.WASHER_ID / 2 - dims.PAD_CENTER_RADIUS - tolerance:.2f} mm",
)
check(
    "ring pad never touches the screw head",
    dims.PAD_RING_INNER > screw_head_radius + tolerance,
    f"margin {dims.PAD_RING_INNER - screw_head_radius - tolerance:.2f} mm",
)
check(
    "ring pad still touches the washer",
    dims.PAD_RING_INNER < dims.WASHER_OD / 2 - tolerance,
    f"margin {dims.WASHER_OD / 2 - tolerance - dims.PAD_RING_INNER:.2f} mm",
)

sys.exit(0 if all_passed else 1)
