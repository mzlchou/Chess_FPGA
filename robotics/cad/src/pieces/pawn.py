"""The pawn. Print it standing up at 100% infill so it has some weight to it.

Add a print pause at the first layer that covers the magnet pockets (about 5.5 mm
up from the bed) and drop in the two magnets. See docs/dimensions.pdf.
"""

from cadgen import step, stl

from lib.pieces import piece_body


@step(out="../../STEP/pieces/pawn.step")
@stl(out="../../STL/pieces/pawn.stl")
def pawn():
    return piece_body("pawn")


if __name__ == "__main__":
    pawn()
