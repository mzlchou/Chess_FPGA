"""Checks the gantry frame and prints the cut list.

It makes sure:
  - the rails let the claw reach every square and capture slot
  - nothing on the frame sits on the board or in the way of a captured piece
  - the claw, lifted all the way with a king hanging from it, passes under the runways
  - at the ends of travel the bridge brackets don't hit the motor or idler plates,
    and the Y carriage doesn't hit the brackets

Run from robotics/cad:  python checks/gantry_check.py
"""

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from cadgen import build123d as bd  # noqa: E402

from lib import claw, dims, gantry  # noqa: E402

all_passed = True


def check(description: str, passed: bool, detail: str = "") -> None:
    global all_passed
    all_passed &= bool(passed)
    print(f"  {'PASS' if passed else 'FAIL'}  {description}  {detail}")


print("travel")
low, high = gantry.BRIDGE_X_RANGE
check(
    "X carriages let the claw reach both capture columns",
    gantry.X_CARRIAGE_RANGE[0] <= low and high <= gantry.X_CARRIAGE_RANGE[1],
    f"{low - gantry.X_CARRIAGE_RANGE[0]:.1f} mm to spare at -X, {gantry.X_CARRIAGE_RANGE[1] - high:.1f} at +X",
)
check(
    "Y carriage reaches the first and last rank",
    gantry.Y_CARRIAGE_RANGE[0] <= -dims.CLAW_REACH_Y and dims.CLAW_REACH_Y <= gantry.Y_CARRIAGE_RANGE[1],
    f"{gantry.Y_CARRIAGE_RANGE[1] - dims.CLAW_REACH_Y:.1f} mm to spare at each end",
)

print("clearances")
board_edge = dims.BOARD_SIZE / 2
frame_inner_y = gantry.POST_Y - gantry.SLEEVE_INNER / 2 - gantry.SLEEVE_WALL  # inner face of the sleeves and feet
check("posts, sleeves and feet stand outside the board", frame_inner_y > board_edge, f"{frame_inner_y - board_edge:.1f} mm gap")

claw_half_y = claw.GUIDE_WALL_OUTER_Y  # the jaws open along X, so this is the claw's widest point in Y
biggest_base = max(base for _, base in dims.PIECES.values()) / 2
check(
    "claw and captured pieces stay clear of the posts",
    max(dims.CLAW_REACH_Y + claw_half_y, dims.CLAW_REACH_Y + biggest_base) < frame_inner_y,
    f"{frame_inner_y - (dims.CLAW_REACH_Y + claw_half_y):.1f} mm to spare",
)

highest_seat = 169.0  # carrying a king over another king with 5 to spare (see dimensions.pdf)
z_mount_allowance = 6.0  # a plate on top of the servo for the Z carriage
claw_top = highest_seat + claw.SERVO_FACE_Z + dims.SERVO_HEIGHT + z_mount_allowance
check(
    "lifted claw passes under the runways",
    claw_top < gantry.RUNWAY_BOTTOM,
    f"claw top at z = {claw_top:.0f}, runways start at {gantry.RUNWAY_BOTTOM:.0f}",
)
tallest = max(height for height, _ in dims.PIECES.values())
check("bridge clears a standing king", gantry.BRIDGE_BOTTOM > tallest + 20, f"{gantry.BRIDGE_BOTTOM - tallest:.0f} mm")

# Solid checks at the ends of travel.
motor_block = gantry.corner_block("motor")
idler_block = gantry.corner_block("idler")
fixed = motor_block + idler_block + gantry.x_motor(1) + gantry.x_idler(1) + gantry.runway(1)
for name, bridge_x in (("-X end", low), ("+X end", high)):
    bracket = bd.Pos(bridge_x, 0, 0) * gantry.bridge_bracket()
    volume = (bracket & fixed).volume
    check(f"bridge bracket clears the frame at the {name}", volume < 1e-3, f"overlap {volume:.3f} mm3")
    for y in (-dims.CLAW_REACH_Y, dims.CLAW_REACH_Y):
        carriage = gantry.y_carriage(bridge_x, y)
        volume = (carriage & (bracket + bd.Pos(bridge_x, 0, 0) * gantry.mirror_to_other_side(gantry.bridge_bracket()))).volume
        check(f"Y carriage at y = {y:+.0f} clears the brackets ({name})", volume < 1e-3, f"overlap {volume:.3f} mm3")

print("cut list (3030 and 2525 extrusion)")
print(f"  2 x 3030 runways   {dims.RUNWAY_LENGTH:.0f} mm  (as is)")
print(f"  1 x 3030 bridge    {dims.BRIDGE_LENGTH:.0f} mm  (as is)")
print(f"  4 x 2525 posts     {gantry.POST_LENGTH:.0f} mm  (cut all four to the same length, square ends)")

print("belt")
loop = 2 * (gantry.IDLER_X - gantry.MOTOR_X) + 2 * math.pi * dims.PULLEY_PITCH_RADIUS
per_side = loop - 2 * gantry.BRACKET_HALF_X + 2 * 60  # 60 mm extra at each end to fold back and zip-tie
print(f"  each X belt is about {per_side:.0f} mm, so {2 * per_side / 1000:.2f} m for both. Add the Y belt once it's designed.")

print("frame size")
x_min = gantry.MOTOR_X - dims.NEMA17_SIZE / 2
x_max = gantry.IDLER_X + 15
y_max = gantry.OUTER_FACE_Y + dims.NEMA17_LENGTH
print(f"  {x_max - x_min:.0f} mm in X by {2 * y_max:.0f} mm in Y, {gantry.BRIDGE_TOP - gantry.BASE_TOP:.0f} mm tall from the base")
print(f"  board center is {(x_min + x_max) / 2:+.0f} mm from the middle of the frame in X (the motors stick out on -X)")

sys.exit(0 if all_passed else 1)
