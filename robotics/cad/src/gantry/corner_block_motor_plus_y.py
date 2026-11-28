"""Corner block with the X motor plate, for the -X end of the +Y runway. Print one.

It's laid flat in its print orientation: the outside face (where the motor
bolts on) is on the bed. 4 perimeters and 40% infill, no supports. The hole the
post slides into prints as a 25 mm bridge, which the MK4 handles fine."""

from cadgen import step, stl
from cadgen import build123d as bd

from lib import gantry


@step(out="../../STEP/gantry/corner_block_motor_plus_y.step")
@stl(out="../../STL/gantry/corner_block_motor_plus_y.stl")
def corner_block_motor_plus_y():
    part = gantry.lay_flat(gantry.corner_block("motor"), bd.Rot(-90, 0, 0))
    part.label = "corner_block_motor_plus_y"
    return part


if __name__ == "__main__":
    corner_block_motor_plus_y()
