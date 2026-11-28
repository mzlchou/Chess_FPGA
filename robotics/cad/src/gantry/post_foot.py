"""Holds the bottom of a post and screws into the plywood base. Print four, flange down.

The flange sticks out on one side. Put that side away from the board."""

from cadgen import step, stl
from cadgen import build123d as bd

from lib import gantry


@step(out="../../STEP/gantry/post_foot.step")
@stl(out="../../STL/gantry/post_foot.stl")
def post_foot():
    part = gantry.post_foot()
    part.label = "post_foot"
    return part


if __name__ == "__main__":
    post_foot()
