"""Checks that the claw can actually grab pieces without knocking anything over.

It's split into sections so you can run them one at a time:

    parts      the claw parts don't run into each other, open or closed
    pawn       a pawn sitting up to GRAB_TOLERANCE off center, in eight directions:
    king         the open claw comes down (checked every 4 mm), then closes, and
    knight       neither step is allowed to touch the piece. Then it checks that
                 the cap really rests on the jaws once the claw lifts.
    neighbors  grabbing a pawn with a king right next to it, pushed 4 mm toward
               the pawn, doesn't hit the king

Run from robotics/cad:
    python checks/claw_check.py            # everything, takes a while
    python checks/claw_check.py pawn king  # just those sections
"""

import itertools
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from cadgen import build123d as bd  # noqa: E402
from lib import dims  # noqa: E402
from lib.claw import make_housing, make_jaw, make_pinion, make_servo_standin, place_jaw  # noqa: E402
from lib.pieces import piece_body  # noqa: E402

all_passed = True


def check(description: str, passed: bool, detail: str = "") -> None:
    global all_passed
    all_passed &= bool(passed)
    print(f"  {'PASS' if passed else 'FAIL'}  {description}  {detail}", flush=True)


def overlap(a, b) -> float:
    return (a & b).volume


JAW = make_jaw()
HOUSING = make_housing()
PINION = make_pinion()
SERVO = make_servo_standin()


def claw_parts(opening: float) -> dict:
    """Every claw part, with the jaws at `opening` (0 closed, 1 open) and the pinion turned to match."""
    pinion_turn = math.degrees(opening * dims.JAW_STROKE / dims.PINION_PITCH_RADIUS)
    return {
        "jaw A": place_jaw(JAW, "a", opening),
        "jaw B": place_jaw(JAW, "b", opening),
        "housing": HOUSING,
        "pinion": bd.Rot(0, 0, pinion_turn) * PINION,
        "servo": SERVO,
    }


def piece_in_claw_frame(kind: str, raised: float = 0.0, x: float = 0.0, y: float = 0.0):
    """A piece placed so its cap sits exactly in the claw seat, then raised and shifted.

    Raising the piece is the same as lowering the claw, which is easier to think about.
    """
    height = dims.PIECES[kind][0]
    return bd.Pos(x, y, -(height - dims.CAP_FLAT_HEIGHT) + raised) * piece_body(kind)


def check_claw_parts() -> None:
    print("claw parts against each other", flush=True)
    for opening in (0.0, 1.0):
        state = "open" if opening else "closed"
        for (name_a, part_a), (name_b, part_b) in itertools.combinations(claw_parts(opening).items(), 2):
            if {name_a, name_b} == {"housing", "servo"}:
                continue  # the servo stand-in sits in its pocket, so they touch by design
            volume = overlap(part_a, part_b)
            check(f"{state}: {name_a} vs {name_b}", volume < 0.05, f"{volume:.3f} mm3")


def check_grabbing(kind: str) -> None:
    print(f"{kind}, up to {dims.GRAB_TOLERANCE} mm off center", flush=True)
    off_center_spots = [(0.0, 0.0)] + [
        (dims.GRAB_TOLERANCE * math.cos(k * math.pi / 4), dims.GRAB_TOLERANCE * math.sin(k * math.pi / 4)) for k in range(8)
    ]
    open_claw, closed_claw = claw_parts(1.0), claw_parts(0.0)
    worst_while_descending = 0.0
    worst_while_closing = 0.0
    for x, y in off_center_spots:
        for height_above_close in range(0, 32, 4):
            # The claw being higher up is the same as the piece being lower in the claw's frame.
            piece = piece_in_claw_frame(kind, raised=dims.CLOSING_DROP - height_above_close, x=x, y=y)
            for part in open_claw.values():
                worst_while_descending = max(worst_while_descending, overlap(piece, part))
        piece = piece_in_claw_frame(kind, raised=dims.CLOSING_DROP, x=x, y=y)
        for part in closed_claw.values():
            worst_while_closing = max(worst_while_closing, overlap(piece, part))
    check("open claw comes down without touching it", worst_while_descending < 0.01, f"worst {worst_while_descending:.3f} mm3")
    check("closing the claw doesn't touch it", worst_while_closing < 0.01, f"worst {worst_while_closing:.3f} mm3")

    seated = piece_in_claw_frame(kind)
    worst = max(overlap(seated, part) for part in closed_claw.values())
    check("seated piece doesn't overlap the claw", worst < 0.05, f"{worst:.3f} mm3")
    # Nudge the seated piece down a hair. If the cap is really resting on the jaw, they overlap.
    resting = overlap(bd.Pos(0, 0, -0.05) * seated, closed_claw["jaw A"])
    check("cap is resting on the jaws", resting > 0, f"{resting:.4f} mm3 after a 0.05 mm nudge")


def check_neighbors() -> None:
    print("grabbing a pawn with a king right next door", flush=True)
    pawn_height = dims.PIECES["pawn"][0]
    open_claw = claw_parts(1.0)
    for where, (dx, dy) in {"to the right": (1, 0), "to the left": (-1, 0), "in front": (0, 1), "diagonal": (1, 1)}.items():
        length = math.hypot(dx, dy)
        distance = dims.SQUARE * length - dims.GRAB_TOLERANCE  # king nudged toward the pawn
        spot = bd.Pos(dx / length * distance, dy / length * distance, -(pawn_height - dims.CAP_FLAT_HEIGHT) + dims.CLOSING_DROP)
        king = spot * piece_body("king")
        worst = max(overlap(king, part) for part in open_claw.values())
        check(f"king {where}", worst < 0.01, f"{worst:.3f} mm3")


SECTIONS = {
    "parts": check_claw_parts,
    "pawn": lambda: check_grabbing("pawn"),
    "king": lambda: check_grabbing("king"),
    "knight": lambda: check_grabbing("knight"),
    "neighbors": check_neighbors,
}

if __name__ == "__main__":
    chosen = sys.argv[1:] or list(SECTIONS)
    unknown = [name for name in chosen if name not in SECTIONS]
    if unknown:
        sys.exit(f"Unknown section: {', '.join(unknown)}. Pick from: {', '.join(SECTIONS)}")
    for name in chosen:
        SECTIONS[name]()
    sys.exit(0 if all_passed else 1)
