"""The bishop. Print it standing up at 100% infill so it has some weight to it."""

from cadgen import step, stl

from lib.pieces import piece_body


@step(out="../../STEP/pieces/bishop.step")
@stl(out="../../STL/pieces/bishop.stl")
def bishop():
    return piece_body("bishop")


if __name__ == "__main__":
    bishop()
