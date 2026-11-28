"""Holds the -Y end of the bridge. The mirror image of bridge_bracket_plus_y. Print one, cheek down."""

from cadgen import step, stl
from cadgen import build123d as bd

from lib import gantry


@step(out="../../STEP/gantry/bridge_bracket_minus_y.step")
@stl(out="../../STL/gantry/bridge_bracket_minus_y.stl")
def bridge_bracket_minus_y():
    part = gantry.lay_flat(gantry.mirror_to_other_side(gantry.bridge_bracket()), bd.Rot(0, -90, 0))
    part.label = "bridge_bracket_minus_y"
    return part


if __name__ == "__main__":
    bridge_bracket_minus_y()
