"""The whole gantry over the board, for the viewer. Not printed.

The bridge is parked so the claw is over the middle of the board, with the
claw lifted to carry height. The Z axis is still a placeholder block until
its carriage is designed.
"""

from cadgen import step
from cadgen import build123d as bd
from cadgen import srgb

from lib import dims, gantry
from claw.claw_assembly import claw_assembly

ALUMINUM = srgb("#B8BEC6")
STEEL = srgb("#8A939C")
PRINTED = srgb("#E07B39")
MOTOR = srgb("#2E3742")
BELT = srgb("#1E1E1E")
BOARD = srgb("#D9C7A3")
WOOD = srgb("#A07850")
PLACEHOLDER = srgb("#7FB3D5")

CLAW_X = 0.0
CLAW_Y = 0.0
SEAT_Z = 120.0  # carry height for an empty claw: well above a standing king


def part(shape, label, color):
    shape.label = label
    shape.color = color
    return shape


@step(out="../../STEP/gantry/frame_assembly.step")
def frame_assembly():
    bridge_x = CLAW_X - dims.CLAW_OFFSET_X
    children = []

    board = gantry.box(-dims.BOARD_SIZE / 2, dims.BOARD_SIZE / 2, -dims.BOARD_SIZE / 2, dims.BOARD_SIZE / 2, gantry.BASE_TOP, 0)
    children.append(part(board, "board", BOARD))
    base = gantry.box(gantry.MOTOR_X - 40, gantry.IDLER_X + 40, -gantry.OUTER_FACE_Y - 45, gantry.OUTER_FACE_Y + 45, gantry.BASE_TOP - 12, gantry.BASE_TOP)
    children.append(part(base, "plywood_base", WOOD))

    for side, name in ((1, "plus_y"), (-1, "minus_y")):
        def this_side(shape):
            return shape if side == 1 else gantry.mirror_to_other_side(shape)

        children.append(part(gantry.runway(side), f"runway_{name}", ALUMINUM))
        children.append(part(gantry.x_rail(side), f"x_rail_{name}", STEEL))
        children.append(part(gantry.x_carriage(bridge_x, side), f"x_carriage_{name}", STEEL))
        children.append(part(this_side(gantry.corner_block("motor")), f"corner_block_motor_{name}", PRINTED))
        children.append(part(this_side(gantry.corner_block("idler")), f"corner_block_idler_{name}", PRINTED))
        children.append(part(bd.Pos(bridge_x, 0, 0) * this_side(gantry.bridge_bracket()), f"bridge_bracket_{name}", PRINTED))
        children.append(part(gantry.x_motor(side), f"x_motor_{name}", MOTOR))
        children.append(part(gantry.x_idler(side), f"x_idler_{name}", STEEL))
        children.append(part(gantry.x_belt(bridge_x, side), f"x_belt_{name}", BELT))
        for end, post_x in zip(("motor_end", "idler_end"), gantry.POST_X):
            children.append(part(gantry.post(post_x, side), f"post_{end}_{name}", ALUMINUM))
            # The feet are built with +Y as the outside, so turn them around on the -Y side.
            foot = bd.Pos(post_x, side * gantry.POST_Y, gantry.BASE_TOP) * bd.Rot(0, 0, 0 if side == 1 else 180) * gantry.post_foot()
            children.append(part(foot, f"post_foot_{end}_{name}", PRINTED))

    children.append(part(gantry.bridge(bridge_x), "bridge", ALUMINUM))
    children.append(part(gantry.y_rail(bridge_x), "y_rail", STEEL))
    carriage = gantry.y_carriage(bridge_x, CLAW_Y)
    children.append(part(carriage, "y_carriage", STEEL))

    # Stand-in for the Z axis until it's designed: a plate on the Y carriage and a block above the claw.
    plate_x = bridge_x + gantry.P3 / 2 + dims.MGN12_HEIGHT
    z_plate = gantry.box(plate_x, plate_x + 6, CLAW_Y - 30, CLAW_Y + 30, gantry.BRIDGE_Z - 40, gantry.BRIDGE_Z + 40)
    z_block = gantry.box(CLAW_X - 20, plate_x + 6, CLAW_Y - 25, CLAW_Y + 25, SEAT_Z + 41, gantry.BRIDGE_Z - 40)
    children.append(part(z_plate + z_block, "z_axis_placeholder", PLACEHOLDER))

    claw = bd.Pos(CLAW_X, CLAW_Y, SEAT_Z) * claw_assembly()
    claw.label = "claw"
    children.append(claw)

    return bd.Compound(children=children, label="frame_assembly")


if __name__ == "__main__":
    frame_assembly()
