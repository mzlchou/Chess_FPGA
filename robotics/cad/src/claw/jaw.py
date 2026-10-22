"""One claw jaw. Print two. Lay it upside down so the flat top of the rack is on the bed."""

from cadgen import step, stl

from lib.claw import make_jaw


@step(out="../../STEP/claw/jaw.step")
@stl(out="../../STL/claw/jaw.stl")
def jaw():
    return make_jaw()


if __name__ == "__main__":
    jaw()
