"""All six pieces in a row, one per square, with their washers, bolts, nuts and magnets.

This one isn't printed. It's for looking at the whole set in the viewer.
"""

from cadgen import step
from cadgen import build123d as bd
from cadgen import srgb

from lib import dims
from lib.pieces import center_nut, center_screw, contact_washer, piece_magnets
from pieces.bishop import bishop
from pieces.contact_plug import contact_plug
from pieces.king import king
from pieces.knight import knight
from pieces.pawn import pawn
from pieces.queen import queen
from pieces.rook import rook

PIECES_IN_ORDER = [("pawn", pawn), ("rook", rook), ("knight", knight), ("bishop", bishop), ("queen", queen), ("king", king)]

PLASTIC = srgb("#E8DCC4")
PLUG = srgb("#2E3742")
STEEL = srgb("#9AA3AD")
BRASS = srgb("#C9A54A")
MAGNET = srgb("#5A6470")


@step(out="../../STEP/pieces/piece_lineup.step")
def piece_lineup():
    row = []
    for square, (name, build_piece) in enumerate(PIECES_IN_ORDER):
        body = build_piece()
        body.color = PLASTIC
        plug = contact_plug()
        plug.color = PLUG
        washer = contact_washer()
        washer.color = BRASS
        magnets = piece_magnets()
        magnets.color = MAGNET
        bolt, nut = center_screw(), center_nut()
        bolt.color = nut.color = STEEL
        hardware = [washer, bolt, nut, magnets]

        piece = bd.Compound(children=[body, plug, *hardware], label=name)
        row.append(bd.Pos(square * dims.SQUARE, 0, 0) * piece)
    return bd.Compound(children=row, label="piece_lineup")


if __name__ == "__main__":
    piece_lineup()
