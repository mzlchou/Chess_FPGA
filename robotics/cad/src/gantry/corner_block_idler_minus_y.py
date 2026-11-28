"""Corner block with the belt idler slot, for the +X end of the -Y runway. Print one.

The mirror image of corner_block_idler_plus_y, printed outside face down."""

from cadgen import step, stl
from cadgen import build123d as bd

from lib import gantry


@step(out="../../STEP/gantry/corner_block_idler_minus_y.step")
@stl(out="../../STL/gantry/corner_block_idler_minus_y.stl")
def corner_block_idler_minus_y():
    part = gantry.lay_flat(gantry.mirror_to_other_side(gantry.corner_block("idler")), bd.Rot(90, 0, 0))
    part.label = "corner_block_idler_minus_y"
    return part


if __name__ == "__main__":
    corner_block_idler_minus_y()
