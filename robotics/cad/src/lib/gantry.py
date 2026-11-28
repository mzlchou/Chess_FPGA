"""The gantry frame: where everything goes, and the printed parts that hold it together.

How it's laid out (looking down on the board, x to the right, y away from you):

    - Four 2525 posts stand at the corners, just outside the board.
    - A printed corner block sits on top of each post. The two 600 mm 3030
      runways rest on the corner blocks, one along each side of the board.
    - An MGN12 rail is bolted on top of each runway. The bridge (the 450 mm
      3030 bar) sits on a printed bracket on each rail's carriage, so it can
      roll the length of the board in X.
    - A third MGN12 rail on the side of the bridge carries the claw in Y.

Each runway has its own X motor at the -X end and an idler at the +X end. The
belt loop runs just outside the runway and is clamped to the bridge bracket.
Both X motors plug into the same driver, so they always move together.

Everything here is in board coordinates (see dims.py). The parts are built for
the +Y side of the board. The -Y side gets mirror images.
"""

from __future__ import annotations

from cadgen import build123d as bd

from lib import dims
from lib.pieces import cylinder


def box(x_min, x_max, y_min, y_max, z_min, z_max) -> bd.Shape:
    """A box given by its corner coordinates. The order of each pair doesn't matter."""
    x_min, x_max = sorted((x_min, x_max))
    y_min, y_max = sorted((y_min, y_max))
    z_min, z_max = sorted((z_min, z_max))
    center = ((x_min + x_max) / 2, (y_min + y_max) / 2, (z_min + z_max) / 2)
    return bd.Pos(*center) * bd.Box(x_max - x_min, y_max - y_min, z_max - z_min)


def rod_along_x(radius, x_start, x_end, y, z) -> bd.Shape:
    x_start, x_end = sorted((x_start, x_end))
    return bd.Pos(x_start, y, z) * bd.Rot(0, 90, 0) * cylinder(radius, 0, x_end - x_start)


def rod_along_y(radius, y_start, y_end, x, z) -> bd.Shape:
    y_start, y_end = sorted((y_start, y_end))
    return bd.Pos(x, y_start, z) * bd.Rot(-90, 0, 0) * cylinder(radius, 0, y_end - y_start)


def mirror_to_other_side(shape: bd.Shape) -> bd.Shape:
    """The same part for the -Y side of the board."""
    return bd.mirror(shape, about=bd.Plane.XZ)


def lay_flat(shape: bd.Shape, rotation: bd.Rot) -> bd.Shape:
    """Turn a part into its print orientation and set it on the bed at the origin."""
    turned = rotation * shape
    bounds = turned.bounding_box()
    center = bounds.center()
    return bd.Pos(-center.X, -center.Y, -bounds.min.Z) * turned


# --- Where the frame goes -----------------------------------------------------------

P3 = dims.RUNWAY_PROFILE
P2 = dims.POST_PROFILE

RUNWAY_Y = dims.RUNWAY_Y
RUNWAY_BOTTOM = dims.RUNWAY_BOTTOM_Z
RUNWAY_TOP = RUNWAY_BOTTOM + P3
# The claw hangs CLAW_OFFSET_X in front of the bridge, so the runways are
# shifted back by that much to keep the claw's reach centered on the board.
RUNWAY_X_MIN = -dims.CLAW_OFFSET_X - dims.RUNWAY_LENGTH / 2
RUNWAY_X_MAX = RUNWAY_X_MIN + dims.RUNWAY_LENGTH
BASE_TOP = -dims.BOARD_THICKNESS  # the plywood base the board and the posts stand on

# Corner blocks
SADDLE_THICKNESS = 6.0  # the runway rests on this
SADDLE_LENGTH = 50.0
SLEEVE_WALL = 3.0
SLEEVE_INNER = P2 + 0.4  # a snug slide-on fit over the post
SLEEVE_OUTER = SLEEVE_INNER + 2 * SLEEVE_WALL
SLEEVE_DEPTH = 30.0
SADDLE_BOTTOM = RUNWAY_BOTTOM - SADDLE_THICKNESS
SLEEVE_BOTTOM = SADDLE_BOTTOM - SLEEVE_DEPTH

# Posts. They stand outside the board in Y, so the board can be lifted out.
POST_Y = dims.BOARD_SIZE / 2 + dims.POST_GAP + P2 / 2
OUTER_FACE_Y = POST_Y + SLEEVE_INNER / 2 + SLEEVE_WALL  # outside face of the corner blocks
POST_X = (RUNWAY_X_MIN + SLEEVE_OUTER / 2, RUNWAY_X_MAX - SLEEVE_OUTER / 2)
FOOT_FLOOR = 3.0
POST_BOTTOM = BASE_TOP + FOOT_FLOOR
POST_LENGTH = SADDLE_BOTTOM - POST_BOTTOM

# X belt. The motor bolts to the outside of a plate on the corner block, and
# its pulley sits on the inside of the plate, just outside the runway.
MOUNT_PLATE_THICKNESS = 6.0
MOUNT_PLATE_INNER_Y = OUTER_FACE_Y - MOUNT_PLATE_THICKNESS
BELT_Y = OUTER_FACE_Y - 11.5  # the middle of the belt, about where a pulley's teeth are on its shaft
PULLEY_Z = RUNWAY_TOP + 2.0
BELT_TOP_Z = PULLEY_Z + dims.PULLEY_PITCH_RADIUS  # the strand that gets clamped to the bridge
MOTOR_X = RUNWAY_X_MIN - 25.0
IDLER_X = RUNWAY_X_MAX + 15.0
IDLER_SLOT = 4.0  # the idler can slide this far either way to tension the belt

# Bridge
X_CARRIAGE_TOP = RUNWAY_TOP + dims.MGN12_HEIGHT
BRACKET_THICKNESS = 6.0
BRIDGE_BOTTOM = X_CARRIAGE_TOP + BRACKET_THICKNESS
BRIDGE_TOP = BRIDGE_BOTTOM + P3
BRIDGE_Z = (BRIDGE_BOTTOM + BRIDGE_TOP) / 2
BRACKET_HALF_X = 20.0
CHEEK_THICKNESS = 5.0
CHEEK_FACE_X = -(P3 / 2 + 0.15)  # the cheek bolts to the bridge's -X face
CLAMP_INNER_Y = BELT_Y - 7.5
CLAMP_OUTER_Y = MOUNT_PLATE_INNER_Y - 1.2  # stays clear of the motor and idler plates

# How far the bridge has to go, and how far the carriages let it go.
BRIDGE_X_RANGE = (-dims.CLAW_REACH_X - dims.CLAW_OFFSET_X, dims.CLAW_REACH_X - dims.CLAW_OFFSET_X)
X_CARRIAGE_RANGE = (RUNWAY_X_MIN + dims.MGN12C_LENGTH / 2, RUNWAY_X_MAX - dims.MGN12C_LENGTH / 2)
Y_CARRIAGE_RANGE = (-dims.Y_RAIL_LENGTH / 2 + dims.MGN12H_LENGTH / 2, dims.Y_RAIL_LENGTH / 2 - dims.MGN12H_LENGTH / 2)


# --- Printed parts ----------------------------------------------------------------


def corner_block(end: str) -> bd.Shape:
    """The block on top of a post, for the +Y runway. end is "motor" (-X end) or "idler" (+X end).

    The runway sits on the saddle and bolts down into it with two M6 screws and
    tee nuts. The post slides up into the sleeve and gets two M5 screws. The
    plate on the outside holds the X motor or the belt idler.
    """
    if end == "motor":
        end_x, inward = RUNWAY_X_MIN, 1
    elif end == "idler":
        end_x, inward = RUNWAY_X_MAX, -1
    else:
        raise ValueError(f"end must be 'motor' or 'idler', not {end!r}")
    post_x = end_x + inward * SLEEVE_OUTER / 2
    sleeve_inner_face_y = POST_Y - SLEEVE_INNER / 2 - SLEEVE_WALL

    saddle = box(end_x, end_x + inward * SADDLE_LENGTH, RUNWAY_Y - P3 / 2, OUTER_FACE_Y, SADDLE_BOTTOM, RUNWAY_BOTTOM)
    sleeve = box(end_x, end_x + inward * SLEEVE_OUTER, sleeve_inner_face_y, OUTER_FACE_Y, SLEEVE_BOTTOM, SADDLE_BOTTOM + 0.01)
    block = saddle + sleeve

    # The plate the motor or idler bolts to. The tall part over the post ties it into the block.
    if end == "motor":
        reach_top, reach_bottom, reach_out = PULLEY_Z + 24.0, PULLEY_Z - 26.0, 50.0
    else:
        reach_top, reach_bottom, reach_out = PULLEY_Z + 14.0, PULLEY_Z - 14.0, 30.0
    block += box(end_x, end_x + inward * SLEEVE_OUTER, MOUNT_PLATE_INNER_Y, OUTER_FACE_Y, SLEEVE_BOTTOM, reach_top)
    block += box(end_x + 0.01 * inward, end_x - inward * reach_out, MOUNT_PLATE_INNER_Y, OUTER_FACE_Y, reach_bottom, reach_top)

    # Hole the post slides into.
    block -= box(post_x - SLEEVE_INNER / 2, post_x + SLEEVE_INNER / 2, POST_Y - SLEEVE_INNER / 2, POST_Y + SLEEVE_INNER / 2,
                 SLEEVE_BOTTOM - 1, SADDLE_BOTTOM)

    # Two M6 screws up into the runway's bottom slot.
    for along in (12.0, SADDLE_LENGTH - 10.0):
        block -= bd.Pos(end_x + inward * along, RUNWAY_Y, 0) * cylinder(dims.M6_CLEARANCE / 2, SADDLE_BOTTOM - 1, RUNWAY_BOTTOM + 1)

    # Two M5 screws into the post's slots, one from the outside and one from the end.
    screw_z = (SLEEVE_BOTTOM + SADDLE_BOTTOM) / 2
    block -= rod_along_y(dims.M5_CLEARANCE / 2, POST_Y, OUTER_FACE_Y + 1, post_x, screw_z)
    block -= rod_along_x(dims.M5_CLEARANCE / 2, end_x - inward, post_x, POST_Y, screw_z)

    if end == "motor":
        # NEMA 17 face: four M3 holes on a 31 mm square and a hole for the boss.
        block -= rod_along_y(dims.NEMA17_BOSS_DIA / 2 + 0.5, MOUNT_PLATE_INNER_Y - 1, OUTER_FACE_Y + 1, MOTOR_X, PULLEY_Z)
        half = dims.NEMA17_HOLE_SPACING / 2
        for dx in (-half, half):
            for dz in (-half, half):
                block -= rod_along_y(1.7, MOUNT_PLATE_INNER_Y - 1, OUTER_FACE_Y + 1, MOTOR_X + dx, PULLEY_Z + dz)
    else:
        # A slot for the idler's M5 bolt. Slide it outward to tighten the belt.
        block -= box(IDLER_X - IDLER_SLOT, IDLER_X + IDLER_SLOT, MOUNT_PLATE_INNER_Y - 1, OUTER_FACE_Y + 1,
                     PULLEY_Z - dims.M5_CLEARANCE / 2, PULLEY_Z + dims.M5_CLEARANCE / 2)
        for x in (IDLER_X - IDLER_SLOT, IDLER_X + IDLER_SLOT):
            block -= rod_along_y(dims.M5_CLEARANCE / 2, MOUNT_PLATE_INNER_Y - 1, OUTER_FACE_Y + 1, x, PULLEY_Z)

    block.label = f"corner_block_{end}"
    return block


def bridge_bracket() -> bd.Shape:
    """Bolts onto the X carriage and holds one end of the bridge, for the +Y runway.

    Built with the carriage centered on x = 0. Four M3 screws go down into the
    carriage, then the bridge sits on top and two M6 screws go through the
    cheek into the bridge's -X slot. The belt's two ends come in from either
    side through the channel in the clamp.
    """
    plate = box(CHEEK_FACE_X - CHEEK_THICKNESS, BRACKET_HALF_X, RUNWAY_Y - 25.0, CLAMP_OUTER_Y, X_CARRIAGE_TOP, BRIDGE_BOTTOM)
    cheek = box(CHEEK_FACE_X - CHEEK_THICKNESS, CHEEK_FACE_X, RUNWAY_Y - 25.0, RUNWAY_Y + P3 / 2, BRIDGE_BOTTOM - 0.01, BRIDGE_Z + 10.0)
    clamp = box(CHEEK_FACE_X - CHEEK_THICKNESS, BRACKET_HALF_X, CLAMP_INNER_Y, CLAMP_OUTER_Y, BELT_TOP_Z - 6.0, X_CARRIAGE_TOP + 0.01)
    bracket = plate + cheek + clamp

    # Belt channel, open on the outside so the belt slides in from the side.
    # Fold each belt end back on itself and zip-tie it. The lump can't pull through.
    bracket -= box(CHEEK_FACE_X - CHEEK_THICKNESS - 1, BRACKET_HALF_X + 1, BELT_Y - dims.BELT_WIDTH / 2 - 0.5, CLAMP_OUTER_Y + 1,
                   BELT_TOP_Z - dims.BELT_THICKNESS / 2 - 0.5, BELT_TOP_Z + dims.BELT_THICKNESS / 2 + 0.6)

    # M3 screws into the carriage, with counterbores so the heads sit under the bridge.
    along, across = dims.MGN12C_HOLES
    for x in (-along / 2, along / 2):
        for y in (RUNWAY_Y - across / 2, RUNWAY_Y + across / 2):
            bracket -= bd.Pos(x, y, 0) * cylinder(1.7, X_CARRIAGE_TOP - 1, BRIDGE_BOTTOM + 1)
            bracket -= bd.Pos(x, y, 0) * cylinder(3.0, BRIDGE_BOTTOM - 3.2, BRIDGE_BOTTOM + 1)

    # M6 screws through the cheek into the bridge.
    for y in (RUNWAY_Y - 15.0, RUNWAY_Y + 5.0):
        bracket -= rod_along_x(dims.M6_CLEARANCE / 2, CHEEK_FACE_X - CHEEK_THICKNESS - 1, CHEEK_FACE_X + 1, y, BRIDGE_Z)

    bracket.label = "bridge_bracket"
    return bracket


FOOT_FLANGE_THICKNESS = 4.0
FOOT_SOCKET_HEIGHT = 18.0


def post_foot() -> bd.Shape:
    """Screws to the plywood base and holds the bottom of a post. Built at the origin, flange down.

    The flange only sticks out on the outside and the ends, so it never sits
    under the board. +Y is the outside.
    """
    outer = SLEEVE_INNER / 2 + SLEEVE_WALL
    foot = box(-27.5, 27.5, -outer, 30.0, 0, FOOT_FLANGE_THICKNESS)
    foot += box(-outer, outer, -outer, outer, 0, FOOT_SOCKET_HEIGHT)
    foot -= box(-SLEEVE_INNER / 2, SLEEVE_INNER / 2, -SLEEVE_INNER / 2, SLEEVE_INNER / 2, FOOT_FLOOR, FOOT_SOCKET_HEIGHT + 1)
    for x, y in ((-22.0, 0.0), (22.0, 0.0), (-15.0, 22.0), (15.0, 22.0)):  # wood screws into the base
        foot -= bd.Pos(x, y, 0) * cylinder(2.25, -1, FOOT_FLANGE_THICKNESS + 1)
    foot -= rod_along_y(dims.M5_CLEARANCE / 2, 0, outer + 1, 0, (FOOT_FLOOR + FOOT_SOCKET_HEIGHT) / 2 + 2)
    foot.label = "post_foot"
    return foot


# --- Bought-part stand-ins --------------------------------------------------------
# Plain shapes the size of the real thing, for the assembly and the checks.


def runway(side: int) -> bd.Shape:
    y = side * RUNWAY_Y
    return box(RUNWAY_X_MIN, RUNWAY_X_MAX, y - P3 / 2, y + P3 / 2, RUNWAY_BOTTOM, RUNWAY_TOP)


def post(x: float, side: int) -> bd.Shape:
    y = side * POST_Y
    return box(x - P2 / 2, x + P2 / 2, y - P2 / 2, y + P2 / 2, POST_BOTTOM, SADDLE_BOTTOM)


def x_rail(side: int) -> bd.Shape:
    y = side * RUNWAY_Y
    return box(RUNWAY_X_MIN, RUNWAY_X_MAX, y - dims.MGN12_RAIL_WIDTH / 2, y + dims.MGN12_RAIL_WIDTH / 2, RUNWAY_TOP, RUNWAY_TOP + dims.MGN12_RAIL_HEIGHT)


def x_carriage(x: float, side: int) -> bd.Shape:
    y = side * RUNWAY_Y
    half = dims.MGN12C_LENGTH / 2
    return box(x - half, x + half, y - dims.MGN12_CARRIAGE_WIDTH / 2, y + dims.MGN12_CARRIAGE_WIDTH / 2, RUNWAY_TOP + 3.0, X_CARRIAGE_TOP)


def bridge(x: float) -> bd.Shape:
    return box(x - P3 / 2, x + P3 / 2, -dims.BRIDGE_LENGTH / 2, dims.BRIDGE_LENGTH / 2, BRIDGE_BOTTOM, BRIDGE_TOP)


def y_rail(bridge_x: float) -> bd.Shape:
    x = bridge_x + P3 / 2
    half = dims.MGN12_RAIL_WIDTH / 2
    return box(x, x + dims.MGN12_RAIL_HEIGHT, -dims.Y_RAIL_LENGTH / 2, dims.Y_RAIL_LENGTH / 2, BRIDGE_Z - half, BRIDGE_Z + half)


def y_carriage(bridge_x: float, y: float) -> bd.Shape:
    x = bridge_x + P3 / 2
    half_width = dims.MGN12_CARRIAGE_WIDTH / 2
    half_length = dims.MGN12H_LENGTH / 2
    return box(x + 3.0, x + dims.MGN12_HEIGHT, y - half_length, y + half_length, BRIDGE_Z - half_width, BRIDGE_Z + half_width)


def x_motor(side: int) -> bd.Shape:
    """NEMA 17 with its shaft and pulley, on the outside of the motor plate."""
    y_face = side * OUTER_FACE_Y
    half = dims.NEMA17_SIZE / 2
    motor = box(MOTOR_X - half, MOTOR_X + half, y_face, y_face + side * dims.NEMA17_LENGTH, PULLEY_Z - half, PULLEY_Z + half)
    motor += rod_along_y(2.5, y_face, y_face - side * dims.NEMA17_SHAFT_LENGTH, MOTOR_X, PULLEY_Z)
    motor += rod_along_y(dims.PULLEY_PITCH_RADIUS, side * (BELT_Y - 4), side * (BELT_Y + 4), MOTOR_X, PULLEY_Z)
    return motor


def x_idler(side: int) -> bd.Shape:
    return rod_along_y(dims.PULLEY_PITCH_RADIUS, side * (BELT_Y - 4), side * (BELT_Y + 4), IDLER_X, PULLEY_Z)


def x_belt(bridge_x: float, side: int) -> bd.Shape:
    """The two straight runs of the belt loop."""
    y0, y1 = side * (BELT_Y - dims.BELT_WIDTH / 2), side * (BELT_Y + dims.BELT_WIDTH / 2)
    t = dims.BELT_THICKNESS / 2
    bottom = box(MOTOR_X, IDLER_X, y0, y1, PULLEY_Z - dims.PULLEY_PITCH_RADIUS - t, PULLEY_Z - dims.PULLEY_PITCH_RADIUS + t)
    top_left = box(MOTOR_X, bridge_x - BRACKET_HALF_X, y0, y1, BELT_TOP_Z - t, BELT_TOP_Z + t)
    top_right = box(bridge_x + BRACKET_HALF_X, IDLER_X, y0, y1, BELT_TOP_Z - t, BELT_TOP_Z + t)
    return bottom + top_left + top_right
