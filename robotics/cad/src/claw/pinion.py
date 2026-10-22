"""The pinion gear. It screws onto the servo horn. Print it flat."""

from cadgen import step, stl

from lib.claw import make_pinion


@step(out="../../STEP/claw/pinion.step")
@stl(out="../../STL/claw/pinion.stl")
def pinion():
    return make_pinion()


if __name__ == "__main__":
    pinion()
