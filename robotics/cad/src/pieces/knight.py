"""The knight. Print it standing up at 100% infill so it has some weight to it."""

from cadgen import step, stl

from lib.pieces import piece_body


@step(out="../../STEP/pieces/knight.step")
@stl(out="../../STL/pieces/knight.stl")
def knight():
    return piece_body("knight")


if __name__ == "__main__":
    knight()
