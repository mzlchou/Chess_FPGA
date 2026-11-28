"""Geometry for the chess pieces, the contact plug and the hardware stand-ins.

Every piece is built from the same three chunks stacked on top of each other:

    head   the mushroom cap the claw grabs (identical on every piece)
    middle the part that makes it look like a rook, a knight, and so on
    foot   the round base that holds the washer, bolt, magnets and resistor

Each piece is built standing up with z = 0 at the contact plane (see dims.py).
"""

from __future__ import annotations

from cadgen import build123d as bd

from lib import dims


# --- Small helpers -------------------------------------------------------------
# build123d centers shapes on the origin by default. These put the bottom of
# the shape at z_bottom instead, which is a lot easier to think about when
# you're stacking pieces of a chess piece.


def _bottom_aligned():
    return (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)


def cylinder(radius: float, z_bottom: float, z_top: float) -> bd.Shape:
    return bd.Pos(0, 0, z_bottom) * bd.Cylinder(radius, z_top - z_bottom, align=_bottom_aligned())


def cone(bottom_radius: float, top_radius: float, z_bottom: float, z_top: float) -> bd.Shape:
    return bd.Pos(0, 0, z_bottom) * bd.Cone(bottom_radius, top_radius, z_top - z_bottom, align=_bottom_aligned())


def box_from_bottom(x: float, y: float, z_bottom: float, size_x: float, size_y: float, height: float) -> bd.Shape:
    return bd.Pos(x, y, z_bottom) * bd.Box(size_x, size_y, height, align=_bottom_aligned())


# --- The parts every piece shares -----------------------------------------------


def foot(base_radius: float) -> bd.Shape:
    bottom = dims.METAL_PROUD
    top = bottom + dims.FOOT_HEIGHT
    return (
        cone(base_radius - 0.6, base_radius, bottom, bottom + 0.6)  # small chamfer so the first layer doesn't squish out
        + cylinder(base_radius, bottom + 0.6, top - 1.0)
        + cone(base_radius, base_radius - 1.0, top - 1.0, top)
        + cone(base_radius - 1.5, dims.STEM_RADIUS, top, dims.STEM_START_Z)
    )


def head(piece_height: float) -> bd.Shape:
    neck_bottom = piece_height - dims.HEAD_HEIGHT
    cap_bottom = piece_height - dims.CAP_HEIGHT
    return (
        cylinder(dims.NECK_RADIUS, neck_bottom, cap_bottom)
        + cone(dims.NECK_RADIUS, dims.CAP_RADIUS, cap_bottom, cap_bottom + dims.CAP_CONE_HEIGHT)
        + cylinder(dims.CAP_RADIUS, cap_bottom + dims.CAP_CONE_HEIGHT, piece_height)
    )


# Heights inside the foot, from the bottom up. The brass washer sits from 0 to
# WASHER_THICKNESS, the plug's flange and the nut sit on top of it, and the two
# magnets sit on either side of the nut.
WASHER_TOP = dims.WASHER_THICKNESS
FLANGE_TOP = WASHER_TOP + dims.FLANGE_POCKET_DEPTH
NUT_BOTTOM = WASHER_TOP + dims.PLUG_FLANGE_THICKNESS
MAGNET_BOTTOM = WASHER_TOP + dims.MAGNET_FLOOR
MAGNET_POCKET_TOP = MAGNET_BOTTOM + dims.PIECE_MAGNET_THICKNESS + 0.2
CAVITY_BOTTOM = MAGNET_POCKET_TOP + dims.MAGNET_ROOF
CAVITY_TOP = CAVITY_BOTTOM + dims.RESISTOR_CAVITY_HEIGHT

# The nut pocket is a tight box so the nut can't spin while you tighten the bolt.
NUT_POCKET_HALF_X = (dims.M3_NUT_CORNERS + dims.FIT_SLIP) / 2
NUT_POCKET_HALF_Y = (dims.M3_NUT_FLATS + dims.FIT_SLIP) / 2
MAGNET_POCKET_RADIUS = (dims.PIECE_MAGNET_DIA + dims.FIT_SLIP) / 2
MAGNET_Y = NUT_POCKET_HALF_Y + dims.MAGNET_WALL + MAGNET_POCKET_RADIUS  # magnets sit at y = +-MAGNET_Y


def magnet_pockets() -> bd.Shape:
    """The two closed pockets the magnets go in. You drop them in during a print pause."""
    pocket = cylinder(MAGNET_POCKET_RADIUS, MAGNET_BOTTOM, MAGNET_POCKET_TOP)
    return bd.Pos(0, MAGNET_Y, 0) * pocket + bd.Pos(0, -MAGNET_Y, 0) * pocket


def resistor_cavity() -> bd.Shape:
    cavity = cylinder(dims.RESISTOR_CAVITY_RADIUS, CAVITY_BOTTOM, CAVITY_TOP)
    roof = cone(dims.RESISTOR_CAVITY_RADIUS, 0.0, CAVITY_TOP, CAVITY_TOP + dims.RESISTOR_CAVITY_RADIUS)  # 45 degrees, no supports
    return cavity + roof


def hollows_in_the_foot() -> bd.Shape:
    """Everything we cut out of the bottom: washer, plug flange, nut, magnets, resistor."""
    washer_pocket = cylinder((dims.WASHER_OD + dims.FIT_SLIP) / 2, -1.0, WASHER_TOP)
    flange_pocket = box_from_bottom(
        0, 0, WASHER_TOP, dims.PLUG_FLANGE_LENGTH + dims.FIT_SLIP, dims.PLUG_FLANGE_WIDTH + dims.FIT_SLIP, dims.FLANGE_POCKET_DEPTH
    )
    nut_pocket = box_from_bottom(0, 0, FLANGE_TOP - 0.01, 2 * NUT_POCKET_HALF_X, 2 * NUT_POCKET_HALF_Y, CAVITY_BOTTOM - FLANGE_TOP + 0.02)

    # A narrow slot so one resistor lead can reach down and be soldered to the
    # washer, out past the end of the plug's flange.
    slot_start = NUT_POCKET_HALF_X - 0.5
    slot_length = dims.LEAD_SLOT_REACH - slot_start
    lead_slot = box_from_bottom(slot_start + slot_length / 2, 0, WASHER_TOP, slot_length, dims.LEAD_SLOT_WIDTH, CAVITY_BOTTOM - WASHER_TOP + 1.0)

    return washer_pocket + flange_pocket + nut_pocket + lead_slot + magnet_pockets() + resistor_cavity()


# --- The middle of each piece ---------------------------------------------------
# Each of these gets the full piece height and builds the shape between the
# stem and the bottom of the neck (called `top` below). Anything above `top`
# has to stay inside the neck radius or the claw jaws will hit it.


def pawn_middle(piece_height: float) -> bd.Shape:
    top = piece_height - dims.HEAD_HEIGHT
    stem = cone(dims.STEM_RADIUS, 5.0, dims.STEM_START_Z, top - 8.0)
    ball = bd.Pos(0, 0, top - 6.0) * bd.Sphere(7.5)
    return stem + ball


def rook_middle(piece_height: float) -> bd.Shape:
    top = piece_height - dims.HEAD_HEIGHT
    tower = cone(dims.STEM_RADIUS, 8.0, dims.STEM_START_Z, top - 6.0) + cylinder(10.0, top - 6.0, top)
    one_notch_pair = box_from_bottom(0, 0, top - 3.0, 24, 4, 3.0)
    battlements = one_notch_pair + bd.Rot(0, 0, 90) * one_notch_pair
    return tower - battlements


def knight_middle(piece_height: float) -> bd.Shape:
    top = piece_height - dims.HEAD_HEIGHT
    # Side view of the horse head, as (forward, up) points. It's chunky on purpose
    # so it prints cleanly. A nicer knight can come later.
    head_outline = [(-7, 22), (7, 22), (8, 27), (14, 34), (15, 37), (10, 40), (6, top), (-6, top), (-9, 36), (-8, 28)]
    side_profile = bd.Plane.XZ * bd.Polygon(*head_outline, align=None)
    horse_head = bd.extrude(side_profile, amount=6, both=True)  # 12 mm thick
    stem = cone(dims.STEM_RADIUS, 7.0, dims.STEM_START_Z, 24.0)
    return stem + horse_head


def bishop_middle(piece_height: float) -> bd.Shape:
    top = piece_height - dims.HEAD_HEIGHT
    mitre_center = top - 9.0
    body = (
        cone(dims.STEM_RADIUS, 5.0, dims.STEM_START_Z, mitre_center - 9.0)
        + cylinder(8.0, mitre_center - 9.0, mitre_center - 7.5)  # collar
        + bd.Pos(0, 0, mitre_center) * bd.Sphere(8.0)
        + cone(8.0, 4.0, mitre_center, top)
    )
    slit = bd.Pos(8.0, 0, mitre_center + 2.0) * bd.Rot(0, 35, 0) * bd.Box(6, 1.6, 14)
    return body - slit


def queen_middle(piece_height: float) -> bd.Shape:
    top = piece_height - dims.HEAD_HEIGHT
    crown_bottom = top - 13.0
    body = (
        cone(dims.STEM_RADIUS, 5.0, dims.STEM_START_Z, crown_bottom - 2.0)
        + cylinder(8.0, crown_bottom - 2.0, crown_bottom)  # collar
        + cone(5.0, 10.0, crown_bottom, top)
    )
    # Four slots through the crown give it eight points.
    slot = box_from_bottom(0, 0, top - 3.0, 24, 3, 3.0)
    for angle in (0, 45, 90, 135):
        body -= bd.Rot(0, 0, angle) * slot
    return body


def king_middle(piece_height: float) -> bd.Shape:
    top = piece_height - dims.HEAD_HEIGHT
    crown_bottom = top - 16.0
    body = (
        cone(dims.STEM_RADIUS, 5.5, dims.STEM_START_Z, crown_bottom - 2.0)
        + cylinder(8.5, crown_bottom - 2.0, crown_bottom)  # collar
        + cone(5.5, 9.5, crown_bottom, top - 2.0)
        + cylinder(10.0, top - 2.0, top)  # band under the neck
    )
    # The cross can't go on top (that's where the claw grabs), so it goes on the front.
    cross_z = crown_bottom + 7.0
    upright = bd.Pos(8.0, 0, cross_z) * bd.Box(3, 2.4, 9)
    crossbar = bd.Pos(8.0, 0, cross_z + 1.5) * bd.Box(3, 7, 2.4)
    return body + upright + crossbar


MIDDLES = {
    "pawn": pawn_middle,
    "rook": rook_middle,
    "knight": knight_middle,
    "bishop": bishop_middle,
    "queen": queen_middle,
    "king": king_middle,
}


def piece_body(kind: str) -> bd.Shape:
    """The printed body of one piece, e.g. piece_body("knight")."""
    height, base_diameter = dims.PIECES[kind]
    body = foot(base_diameter / 2) + MIDDLES[kind](height) + head(height)
    body -= hollows_in_the_foot()
    body.label = f"{kind}_body"
    return body


# --- Contact plug -----------------------------------------------------------------


def hexagon_prism(flats: float, z_bottom: float, z_top: float) -> bd.Shape:
    """A hexagon given by its size across the flats, with two flats facing +-Y."""
    hexagon = bd.RegularPolygon(flats / 2, 6, major_radius=False)
    return bd.Pos(0, 0, z_bottom) * bd.extrude(hexagon, z_top - z_bottom)


def make_contact_plug() -> bd.Shape:
    """Printed insulator that sits in the washer hole and holds the M3 hex bolt."""
    flange_top = WASHER_TOP + dims.PLUG_FLANGE_THICKNESS
    plug = cylinder(dims.PLUG_RADIUS, 0.0, WASHER_TOP)
    plug += box_from_bottom(0, 0, WASHER_TOP, dims.PLUG_FLANGE_LENGTH, dims.PLUG_FLANGE_WIDTH, dims.PLUG_FLANGE_THICKNESS)

    bolt_hole = cylinder(dims.M3_CLEARANCE / 2, -1.0, flange_top + 1.0)
    head_pocket = hexagon_prism(dims.M3_HEAD_FLATS + dims.FIT_SLIP, -1.0, dims.M3_HEAD_HEIGHT)

    plug = plug - bolt_hole - head_pocket
    plug.label = "contact_plug"
    return plug


# --- Hardware stand-ins ---------------------------------------------------------
# These aren't printed. They're simple shapes of the bought parts so the
# assemblies and fit checks have something to look at.


def contact_washer() -> bd.Shape:
    washer = cylinder(dims.WASHER_OD / 2, 0.0, dims.WASHER_THICKNESS)
    washer -= cylinder(dims.WASHER_ID / 2, -1.0, dims.WASHER_THICKNESS + 1.0)
    washer.label = "m10_brass_washer"
    return washer


def center_screw() -> bd.Shape:
    """The M3 hex-head bolt, head down, with the head's flat top on the contact plane."""
    screw = hexagon_prism(dims.M3_HEAD_FLATS, 0.0, dims.M3_HEAD_HEIGHT)
    screw += cylinder(1.5, dims.M3_HEAD_HEIGHT, dims.M3_HEAD_HEIGHT + dims.SCREW_LENGTH)
    screw.label = "m3_hex_bolt"
    return screw


def center_nut() -> bd.Shape:
    nut = hexagon_prism(dims.M3_NUT_FLATS, NUT_BOTTOM, NUT_BOTTOM + dims.M3_NUT_THICKNESS)
    nut -= cylinder(1.5, NUT_BOTTOM - 1.0, NUT_BOTTOM + dims.M3_NUT_THICKNESS + 1.0)
    nut.label = "m3_nut"
    return nut


def piece_magnets() -> bd.Shape:
    magnet = cylinder(dims.PIECE_MAGNET_DIA / 2, MAGNET_BOTTOM, MAGNET_BOTTOM + dims.PIECE_MAGNET_THICKNESS)
    magnets = bd.Pos(0, MAGNET_Y, 0) * magnet + bd.Pos(0, -MAGNET_Y, 0) * magnet
    magnets.label = "d52_magnets"
    return magnets
