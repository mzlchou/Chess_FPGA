"""Corner block with the X motor plate, for the -X end of the -Y runway. Print one.

The mirror image of corner_block_motor_plus_y, printed the same way: outside face down."""

from cadgen import step, stl
from cadgen import build123d as bd

from lib import gantry


@step(out="../../STEP/gantry/corner_block_motor_minus_y.step")
@stl(out="../../STL/gantry/corner_block_motor_minus_y.stl")
def corner_block_motor_minus_y():
    part = gantry.lay_flat(gantry.mirror_to_other_side(gantry.corner_block("motor")), bd.Rot(90, 0, 0))
    part.label = "corner_block_motor_minus_y"
    return part


if __name__ == "__main__":
    corner_block_motor_minus_y()
