"""The queen. Print it standing up at 100% infill so it has some weight to it."""

from cadgen import step, stl

from lib.pieces import piece_body


@step(out="../../STEP/pieces/queen.step")
@stl(out="../../STL/pieces/queen.stl")
def queen():
    return piece_body("queen")


if __name__ == "__main__":
    queen()
