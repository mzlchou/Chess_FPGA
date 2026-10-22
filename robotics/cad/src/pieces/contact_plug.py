"""The little insulating plug in the bottom of every piece. You need one per piece. Print it flange side down."""

from cadgen import step, stl

from lib.pieces import make_contact_plug


@step(out="../../STEP/pieces/contact_plug.step")
@stl(out="../../STL/pieces/contact_plug.stl")
def contact_plug():
    return make_contact_plug()


if __name__ == "__main__":
    contact_plug()
