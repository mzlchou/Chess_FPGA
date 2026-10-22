"""A 2x2 chunk of the board for testing piece detection before we build the whole thing.

Cut copper tape along the engraved circles on each square: a small dot in the
middle and a ring around it. Wires come up through the two holes and get
soldered to the tape. The rails underneath leave room for the wiring.

Print it upside down so the pad side is on the bed and comes out flat.
"""

from cadgen import step, stl
from cadgen import build123d as bd

from lib import dims
from lib.pieces import box_from_bottom, cylinder

SQUARES_PER_SIDE = 2
PLATE_THICKNESS = 4.0
RAIL_WIDTH = 4.0
RAIL_HEIGHT = 6.0  # space for wires under the plate
GROOVE_WIDTH = 0.6
GROOVE_DEPTH = 0.4
WIRE_HOLE_DIA = 1.6
RING_WIRE_HOLE_X = (dims.PAD_RING_INNER + dims.PAD_RING_OUTER) / 2  # halfway across the ring pad


def engraved_circle(radius: float, surface_z: float) -> bd.Shape:
    """A thin circular groove, used as a cutting guide for the copper tape."""
    outer = cylinder(radius + GROOVE_WIDTH / 2, surface_z - GROOVE_DEPTH, surface_z + 1)
    inner = cylinder(radius - GROOVE_WIDTH / 2, surface_z - GROOVE_DEPTH - 1, surface_z + 2)
    return outer - inner


@step(out="../../STEP/board/tile_2x2.step")
@stl(out="../../STL/board/tile_2x2.stl")
def tile_2x2():
    width = SQUARES_PER_SIDE * dims.SQUARE
    surface = RAIL_HEIGHT + PLATE_THICKNESS

    plate = box_from_bottom(0, 0, RAIL_HEIGHT, width, width, PLATE_THICKNESS)
    rails = box_from_bottom(0, 0, 0, width, width, RAIL_HEIGHT) - box_from_bottom(
        0, 0, 0, width - 2 * RAIL_WIDTH, width - 2 * RAIL_WIDTH, RAIL_HEIGHT
    )
    tile = plate + rails

    # Lines between the squares.
    for i in range(1, SQUARES_PER_SIDE):
        line_at = -width / 2 + i * dims.SQUARE
        tile -= box_from_bottom(line_at, 0, surface - GROOVE_DEPTH, GROOVE_WIDTH, width, 1)
        tile -= box_from_bottom(0, line_at, surface - GROOVE_DEPTH, width, GROOVE_WIDTH, 1)

    # Pad outlines and wire holes on every square.
    for column in range(SQUARES_PER_SIDE):
        for row in range(SQUARES_PER_SIDE):
            square_x = -width / 2 + (column + 0.5) * dims.SQUARE
            square_y = -width / 2 + (row + 0.5) * dims.SQUARE
            at_square = bd.Pos(square_x, square_y, 0)
            for radius in (dims.PAD_CENTER_RADIUS, dims.PAD_RING_INNER, dims.PAD_RING_OUTER):
                tile -= at_square * engraved_circle(radius, surface)
            tile -= at_square * cylinder(WIRE_HOLE_DIA / 2, RAIL_HEIGHT - 1, surface + 1)
            tile -= at_square * bd.Pos(RING_WIRE_HOLE_X, 0, 0) * cylinder(WIRE_HOLE_DIA / 2, RAIL_HEIGHT - 1, surface + 1)

    # Shift down so the pad surface is z = 0, the same as the bottom of a piece.
    tile = bd.Pos(0, 0, -surface) * tile
    tile.label = "board_tile_2x2"
    return tile


if __name__ == "__main__":
    tile_2x2()
