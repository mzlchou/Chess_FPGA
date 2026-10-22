"""A spur gear (the pinion) and a straight rack that meshes with it.

Standard 20 degree pressure angle involute teeth. The pinion has a tooth
pointing straight up +Y, and the rack has a gap centered at x = 0, so a rack
placed above the pinion meshes without any fiddling.

The backlash value shaves a little off every tooth so printed gears don't bind.
"""

from __future__ import annotations

import math

from cadgen import build123d as bd

PRESSURE_ANGLE = math.radians(20.0)


def _involute(angle: float) -> float:
    return math.tan(angle) - angle


def pinion_outline(module: float, teeth: int, backlash: float = 0.15, points_per_flank: int = 6) -> list[tuple[float, float]]:
    """The 2D outline of the pinion as a list of (x, y) points."""
    pitch_radius = module * teeth / 2
    base_radius = pitch_radius * math.cos(PRESSURE_ANGLE)
    tip_radius = pitch_radius + module
    root_radius = pitch_radius - 1.25 * module
    flank_start = max(base_radius, root_radius)

    # Half the angular width of one tooth, measured at the pitch circle.
    half_tooth_angle = math.pi / (2 * teeth) - backlash / (4 * pitch_radius)

    def flank_angle(radius: float) -> float:
        """How far (in radians) the tooth flank is from the tooth's centerline at this radius."""
        pressure_here = math.acos(min(1.0, base_radius / radius))
        return half_tooth_angle + _involute(PRESSURE_ANGLE) - _involute(pressure_here)

    def polar(radius: float, angle: float) -> tuple[float, float]:
        return (radius * math.cos(angle), radius * math.sin(angle))

    flank_radii = [flank_start + (tip_radius - flank_start) * i / points_per_flank for i in range(points_per_flank + 1)]

    outline: list[tuple[float, float]] = []
    for tooth in range(teeth):
        center = math.pi / 2 + tooth * 2 * math.pi / teeth  # tooth 0 points along +Y
        outline.append(polar(root_radius, center - flank_angle(flank_start)))
        outline += [polar(r, center - flank_angle(r)) for r in flank_radii]  # up one side
        outline += [polar(r, center + flank_angle(r)) for r in reversed(flank_radii)]  # down the other
        outline.append(polar(root_radius, center + flank_angle(flank_start)))
    return outline


def pinion(module: float, teeth: int, thickness: float, backlash: float = 0.15) -> bd.Shape:
    outline = bd.Polygon(*pinion_outline(module, teeth, backlash), align=None)
    return bd.extrude(outline, thickness)


def rack_teeth(module: float, x_start: float, x_end: float, pitch_line_y: float, thickness: float, backlash: float = 0.15) -> bd.Shape:
    """Rack teeth from x_start to x_end, pointing down toward -Y.

    A rack tooth is just a trapezoid: straight sides at the pressure angle.
    """
    tooth_pitch = math.pi * module
    addendum, dedendum = module, 1.25 * module
    tip_y = pitch_line_y - addendum
    root_y = pitch_line_y + dedendum
    half_thickness = tooth_pitch / 4 - backlash / 4  # half a tooth, measured on the pitch line
    slope = math.tan(PRESSURE_ANGLE)

    teeth = None
    first, last = math.floor(x_start / tooth_pitch) - 1, math.ceil(x_end / tooth_pitch) + 1
    for k in range(first, last):
        tooth_center = (k + 0.5) * tooth_pitch  # teeth sit between the gaps at k * pitch
        trapezoid = [
            (tooth_center - half_thickness - dedendum * slope, root_y + 0.01),
            (tooth_center - half_thickness + addendum * slope, tip_y),
            (tooth_center + half_thickness - addendum * slope, tip_y),
            (tooth_center + half_thickness + dedendum * slope, root_y + 0.01),
        ]
        tooth = bd.extrude(bd.Polygon(*trapezoid, align=None), thickness)
        teeth = tooth if teeth is None else teeth + tooth

    # We made a few extra teeth past each end. Trim them to the requested length.
    keep = bd.Pos((x_start + x_end) / 2, (tip_y + root_y) / 2, thickness / 2) * bd.Box(x_end - x_start, root_y - tip_y + 0.1, thickness + 1)
    return teeth & keep
