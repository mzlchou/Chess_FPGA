"""The king. Print it standing up at 100% infill so it has some weight to it."""

from cadgen import step, stl

from lib.pieces import piece_body


@step(out="../../STEP/pieces/king.step")
@stl(out="../../STL/pieces/king.stl")
def king():
    return piece_body("king")


if __name__ == "__main__":
    king()
