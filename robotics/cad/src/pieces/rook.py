"""The rook. Print it standing up at 100% infill so it has some weight to it."""

from cadgen import step, stl

from lib.pieces import piece_body


@step(out="../../STEP/pieces/rook.step")
@stl(out="../../STL/pieces/rook.stl")
def rook():
    return piece_body("rook")


if __name__ == "__main__":
    rook()
