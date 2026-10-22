"""The claw body: holds the servo, guides the racks, bolts to the Z carriage. Print it upside down."""

from cadgen import step, stl

from lib.claw import make_housing


@step(out="../../STEP/claw/housing.step")
@stl(out="../../STL/claw/housing.stl")
def housing():
    return make_housing()


if __name__ == "__main__":
    housing()
