"""The claw that picks up pieces by their mushroom cap.

How it moves: one servo turns a pinion gear. There's a rack on each side of
the pinion, and each rack is part of a jaw, so turning the servo slides the
two jaws apart or together along X.

How it grabs: the jaws close to a fixed position under the cap. They don't
squeeze anything. When the claw lifts, the cap's cone drops into the cone cut
into the jaw lips, and the piece centers itself.

Coordinates: the claw axis is Z, and z = 0 is the seat plane (where the top of
the cap cone sits when a piece is hanging in the claw). Jaw A is the one on
the -X side. Jaw B is the same part turned 180 degrees.
"""

from __future__ import annotations

import math

from cadgen import build123d as bd

from lib import dims
from lib import gears
from lib.pieces import cone, cylinder

# Where things end up, worked out from dims.py.
RACK_TOOTH_ROOT_Y = dims.PINION_PITCH_RADIUS + 1.25 * dims.GEAR_MODULE
RACK_BACK_Y = RACK_TOOTH_ROOT_Y + dims.RACK_BACKING
RACK_BOTTOM = dims.RACK_BOTTOM_Z
RACK_TOP = dims.RACK_BOTTOM_Z + dims.RACK_THICKNESS
RACK_CHAMFER = 2.5  # rides on a matching 45 degree ledge in the housing
FINGER_OUTER_X = -(dims.JAW_FINGER_INNER_X + dims.JAW_FINGER_THICKNESS)
FINGER_INNER_X = -dims.JAW_FINGER_INNER_X
RACK_FREE_END_X = 6.0 + dims.JAW_STROKE  # long enough to stay in mesh when fully open

HOUSING_BOTTOM = RACK_TOP + dims.SLIDING_CLEARANCE
SERVO_FACE_Z = RACK_TOP + dims.HORN_CLEARANCE
HOUSING_TOP = SERVO_FACE_Z + dims.SERVO_FACE_TO_TAB  # the servo tabs sit on this surface
GUIDE_WALL_INNER_Y = RACK_BACK_Y + dims.SLIDING_CLEARANCE
GUIDE_WALL_OUTER_Y = GUIDE_WALL_INNER_Y + dims.GUIDE_WALL_THICKNESS
LEDGE_BOTTOM = RACK_BOTTOM - 1.5


def _box(x_min, x_max, y_min, y_max, z_min, z_max) -> bd.Shape:
    """A box given by its corner coordinates instead of its center and size."""
    center = ((x_min + x_max) / 2, (y_min + y_max) / 2, (z_min + z_max) / 2)
    return bd.Pos(*center) * bd.Box(x_max - x_min, y_max - y_min, z_max - z_min)


def _prism_along_x(yz_points, x_start, x_end) -> bd.Shape:
    """Draw a shape in the YZ plane and stretch it along X."""
    face = bd.Plane.YZ * bd.Polygon(*yz_points, align=None)
    return bd.Pos(x_start, 0, 0) * bd.extrude(face, x_end - x_start)


# --- Jaw ---------------------------------------------------------------------------


def make_jaw() -> bd.Shape:
    """Jaw A, in the closed position. Print two of these."""
    rack = _box(FINGER_OUTER_X, RACK_FREE_END_X, RACK_TOOTH_ROOT_Y, RACK_BACK_Y, RACK_BOTTOM, RACK_TOP)
    chamfer = [
        (RACK_BACK_Y - RACK_CHAMFER, RACK_BOTTOM - 0.1),
        (RACK_BACK_Y + 0.1, RACK_BOTTOM - 0.1),
        (RACK_BACK_Y + 0.1, RACK_BOTTOM + RACK_CHAMFER),
    ]
    rack -= _prism_along_x(chamfer, FINGER_OUTER_X - 1, RACK_FREE_END_X + 1)
    teeth = bd.Pos(0, 0, RACK_BOTTOM) * gears.rack_teeth(
        dims.GEAR_MODULE, -12.0, RACK_FREE_END_X, dims.PINION_PITCH_RADIUS, dims.RACK_THICKNESS
    )

    # The crossbar ties the rack to the finger, and the finger hangs down past the cap.
    crossbar = _box(FINGER_OUTER_X, FINGER_INNER_X, -dims.JAW_FINGER_HALF_WIDTH, RACK_BACK_Y, RACK_BOTTOM, RACK_TOP)
    finger = _box(FINGER_OUTER_X, FINGER_INNER_X, -dims.JAW_FINGER_HALF_WIDTH, dims.JAW_FINGER_HALF_WIDTH, -dims.JAW_LIP_THICKNESS, RACK_BOTTOM)

    # The lip reaches in under the cap. Its inner edge is a half circle with a
    # 45 degree countersink on top, which is the seat the cap cone drops into.
    lip = _box(FINGER_INNER_X, 0.0, -dims.JAW_LIP_HALF_WIDTH, dims.JAW_LIP_HALF_WIDTH, -dims.JAW_LIP_THICKNESS, 0.0)
    lip -= cylinder(dims.SEAT_RADIUS, -dims.JAW_LIP_THICKNESS - 1, 1.0)
    lip -= cone(dims.SEAT_RADIUS, dims.CAP_RADIUS, -(dims.CAP_RADIUS - dims.SEAT_RADIUS), 0.0)

    # A 45 degree brace between the finger and the lip so the lip prints without supports.
    brace_outline = bd.Plane.XZ * bd.Polygon((FINGER_INNER_X, 0.0), (FINGER_INNER_X + 4.0, 0.0), (FINGER_INNER_X, 4.0), align=None)
    brace = bd.extrude(brace_outline, dims.JAW_LIP_HALF_WIDTH, both=True)

    part = rack + teeth + crossbar + finger + lip + brace
    part.label = "claw_jaw"
    return part


def place_jaw(jaw_shape: bd.Shape, side: str, opening: float) -> bd.Shape:
    """Put a jaw where it belongs. side is "a" or "b"; opening goes from 0 (closed) to 1 (open)."""
    travel = dims.JAW_STROKE * opening
    if side == "a":
        return bd.Pos(-travel, 0, 0) * jaw_shape
    return bd.Pos(travel, 0, 0) * bd.Rot(0, 0, 180) * jaw_shape


# --- Pinion -------------------------------------------------------------------------


def make_pinion() -> bd.Shape:
    gear = bd.Pos(0, 0, RACK_BOTTOM) * gears.pinion(dims.GEAR_MODULE, dims.PINION_TEETH, dims.RACK_THICKNESS)
    gear -= cylinder(2.5, RACK_BOTTOM - 1, RACK_TOP + 1)  # so you can reach the horn screw from below
    gear -= cylinder(4.0, RACK_TOP - 1.5, RACK_TOP + 1)  # recess for the horn's hub
    gear.label = "claw_pinion"
    return gear


# --- Housing ------------------------------------------------------------------------


def make_housing() -> bd.Shape:
    """Holds the servo on top and guides both racks underneath."""
    half_length = dims.GUIDE_HALF_LENGTH
    body = _box(-half_length, half_length, -GUIDE_WALL_OUTER_Y, GUIDE_WALL_OUTER_Y, HOUSING_BOTTOM, HOUSING_TOP)

    # Each rack hangs on a 45 degree ledge that matches the chamfer on the rack,
    # with a little sliding clearance between them. 45 degrees also means the
    # ledge prints fine with the housing upside down.
    clearance = dims.SLIDING_CLEARANCE * math.sqrt(2)
    ledge_inner_y = RACK_BACK_Y - RACK_CHAMFER - (RACK_BOTTOM - LEDGE_BOTTOM) + clearance
    ledge_top = GUIDE_WALL_INNER_Y - (RACK_BACK_Y - RACK_CHAMFER - RACK_BOTTOM + clearance)
    wall = _box(-half_length, half_length, GUIDE_WALL_INNER_Y, GUIDE_WALL_OUTER_Y, LEDGE_BOTTOM, HOUSING_BOTTOM + 0.5)
    ledge = _prism_along_x(
        [(GUIDE_WALL_INNER_Y + 0.01, LEDGE_BOTTOM), (GUIDE_WALL_INNER_Y + 0.01, ledge_top), (ledge_inner_y, LEDGE_BOTTOM)],
        -half_length,
        half_length,
    )
    one_side = wall + ledge
    body += one_side
    body += bd.Rot(0, 0, 180) * one_side

    # Room for the servo horn to swing, then the pocket the servo drops into.
    body -= cylinder(dims.HORN_SWEEP_RADIUS, HOUSING_BOTTOM - 1, SERVO_FACE_Z)
    servo_y = dims.SERVO_SHAFT_OFFSET
    body -= _box(
        -(dims.SERVO_WIDTH / 2 + 0.25), dims.SERVO_WIDTH / 2 + 0.25,
        servo_y - dims.SERVO_LENGTH / 2 - 0.25, servo_y + dims.SERVO_LENGTH / 2 + 0.25,
        SERVO_FACE_Z - 0.01, HOUSING_TOP + 1,
    )

    # Pilot holes for the servo's M2 tab screws.
    for hole_y in (servo_y - dims.SERVO_HOLE_SPACING / 2, servo_y + dims.SERVO_HOLE_SPACING / 2):
        body -= bd.Pos(0, hole_y, 0) * cylinder(0.9, HOUSING_TOP - 6, HOUSING_TOP + 1)

    # Four M3 heat-set inserts on top for bolting the claw to the Z carriage.
    for x in (-11.0, 11.0):
        for y in (-18.0, 18.0):
            body -= bd.Pos(x, y, 0) * cylinder(2.0, HOUSING_TOP - 5, HOUSING_TOP + 1)

    body.label = "claw_housing"
    return body


# --- Servo stand-in -------------------------------------------------------------------


def make_servo_standin() -> bd.Shape:
    """A plain block the size of an MG90S, sitting upside down in the housing. Not printed."""
    case_y = dims.SERVO_SHAFT_OFFSET
    case = _box(
        -dims.SERVO_WIDTH / 2, dims.SERVO_WIDTH / 2,
        case_y - dims.SERVO_LENGTH / 2, case_y + dims.SERVO_LENGTH / 2,
        SERVO_FACE_Z, SERVO_FACE_Z + dims.SERVO_HEIGHT,
    )
    tabs = _box(
        -dims.SERVO_TAB_WIDTH / 2, dims.SERVO_TAB_WIDTH / 2,
        case_y - dims.SERVO_TAB_SPAN / 2, case_y + dims.SERVO_TAB_SPAN / 2,
        HOUSING_TOP, HOUSING_TOP + dims.SERVO_TAB_THICKNESS,
    )
    shaft = cylinder(2.4, RACK_TOP, SERVO_FACE_Z)
    horn = _box(-3.0, 3.0, -15.0, 15.0, RACK_TOP + 0.1, RACK_TOP + 2.0)
    servo = case + tabs + shaft + horn
    servo.label = "mg90s_standin"
    return servo
