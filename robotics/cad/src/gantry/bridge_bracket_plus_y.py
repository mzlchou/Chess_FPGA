"""Holds the +Y end of the bridge on the X carriage, and clamps the belt. Print one.

Laid on its side with the cheek (the part that bolts to the bridge) on the bed,
so every hole prints cleanly. 4 perimeters, 40% infill, no supports."""

from cadgen import step, stl
from cadgen import build123d as bd

from lib import gantry


@step(out="../../STEP/gantry/bridge_bracket_plus_y.step")
@stl(out="../../STL/gantry/bridge_bracket_plus_y.stl")
def bridge_bracket_plus_y():
    part = gantry.lay_flat(gantry.bridge_bracket(), bd.Rot(0, -90, 0))
    part.label = "bridge_bracket_plus_y"
    return part


if __name__ == "__main__":
    bridge_bracket_plus_y()
