"""Geometry for the chess pieces, the contact plug and the hardware stand-ins.

Every piece is built from the same three chunks stacked on top of each other:

    head   the mushroom cap the claw grabs (identical on every piece)
    middle the part that makes it look like a rook, a knight, and so on
    foot   the round base that holds the washer, screw and resistor

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


def hollows_in_the_foot() -> bd.Shape:
    """Everything we cut out of the bottom: washer pocket, plug pocket, resistor cavity."""
    washer_top = dims.WASHER_THICKNESS
    flange_top = washer_top + dims.FLANGE_POCKET_DEPTH
    cavity_top = flange_top + dims.RESISTOR_CAVITY_HEIGHT

    washer_pocket = cylinder((dims.WASHER_OD + dims.FIT_SLIP) / 2, -1.0, washer_top)
    flange_pocket = cylinder(dims.FLANGE_POCKET_RADIUS, washer_top, flange_top)
    resistor_cavity = cylinder(dims.RESISTOR_CAVITY_RADIUS, flange_top, cavity_top)
    cavity_roof = cone(dims.RESISTOR_CAVITY_RADIUS, 0.0, cavity_top, cavity_top + dims.RESISTOR_CAVITY_RADIUS)  # 45 degrees, no supports

    # A narrow slot so one resistor lead can reach down and be soldered to the washer.
    slot_start = dims.RESISTOR_CAVITY_RADIUS - 1.0
    slot_length = dims.LEAD_SLOT_REACH - slot_start
    lead_slot = box_from_bottom(slot_start + slot_length / 2, 0, washer_top, slot_length, dims.LEAD_SLOT_WIDTH, 4.0)

    return washer_pocket + flange_pocket + resistor_cavity + cavity_roof + lead_slot


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


def make_contact_plug() -> bd.Shape:
    """Printed insulator that sits in the washer hole and holds the M3 center screw."""
    washer_top = dims.WASHER_THICKNESS
    flange_top = washer_top + dims.PLUG_FLANGE_THICKNESS
    plug = cylinder(dims.PLUG_RADIUS, 0.0, washer_top) + cylinder(dims.PLUG_FLANGE_RADIUS, washer_top, flange_top)

    screw_hole = cylinder(dims.M3_CLEARANCE / 2, -1.0, flange_top + 1.0)
    countersink_depth = (dims.M3_COUNTERSINK_DIA - dims.M3_CLEARANCE) / 2  # 90 degree countersink
    countersink = cone(dims.M3_COUNTERSINK_DIA / 2, dims.M3_CLEARANCE / 2, 0.0, countersink_depth)
    countersink += cylinder(dims.M3_COUNTERSINK_DIA / 2, -1.0, 0.0)

    plug = plug - screw_hole - countersink
    plug.label = "contact_plug"
    return plug


# --- Hardware stand-ins ---------------------------------------------------------
# These aren't printed. They're simple shapes of the bought parts so the
# assemblies and fit checks have something to look at.


def contact_washer() -> bd.Shape:
    washer = cylinder(dims.WASHER_OD / 2, 0.0, dims.WASHER_THICKNESS)
    washer -= cylinder(dims.WASHER_ID / 2, -1.0, dims.WASHER_THICKNESS + 1.0)
    washer.label = "m12_washer"
    return washer


def center_screw() -> bd.Shape:
    head_height = (dims.M3_COUNTERSINK_DIA - 3.0) / 2
    screw = cone(dims.M3_COUNTERSINK_DIA / 2, 1.5, 0.0, head_height) + cylinder(1.5, head_height, dims.SCREW_LENGTH)
    screw.label = "m3_countersunk_screw"
    return screw


def center_nut() -> bd.Shape:
    bottom = dims.WASHER_THICKNESS + dims.PLUG_FLANGE_THICKNESS
    hexagon = bd.RegularPolygon(dims.M3_NUT_FLATS / 2, 6, major_radius=False)
    nut = bd.Pos(0, 0, bottom) * bd.extrude(hexagon, dims.M3_NUT_THICKNESS)
    nut -= cylinder(1.5, bottom - 1.0, bottom + dims.M3_NUT_THICKNESS + 1.0)
    nut.label = "m3_nut"
    return nut
