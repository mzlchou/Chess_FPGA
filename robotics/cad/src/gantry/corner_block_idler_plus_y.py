"""Corner block with the belt idler slot, for the +X end of the +Y runway. Print one.

Printed with the outside face on the bed, like the motor blocks."""

from cadgen import step, stl
from cadgen import build123d as bd

from lib import gantry


@step(out="../../STEP/gantry/corner_block_idler_plus_y.step")
@stl(out="../../STL/gantry/corner_block_idler_plus_y.stl")
def corner_block_idler_plus_y():
    part = gantry.lay_flat(gantry.corner_block("idler"), bd.Rot(-90, 0, 0))
    part.label = "corner_block_idler_plus_y"
    return part


if __name__ == "__main__":
    corner_block_idler_plus_y()
