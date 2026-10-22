"""The claw, closed, with a pawn hanging in it. For the viewer, not for printing."""

from cadgen import step
from cadgen import build123d as bd
from cadgen import srgb

from lib import dims
from lib.claw import make_servo_standin, place_jaw
from claw.housing import housing
from claw.jaw import jaw
from claw.pinion import pinion
from pieces.pawn import pawn


@step(out="../../STEP/claw/claw_assembly.step")
def claw_assembly():
    claw_body = housing()
    claw_body.color = srgb("#3D6FA8")

    gear = pinion()
    gear.color = srgb("#E0A030")

    jaw_a = place_jaw(jaw(), "a", opening=0.0)
    jaw_b = place_jaw(jaw(), "b", opening=0.0)
    jaw_a.label, jaw_b.label = "jaw_a", "jaw_b"
    for one_jaw in (jaw_a, jaw_b):
        one_jaw.color = srgb("#D9D9D9")

    servo = make_servo_standin()
    servo.color = srgb("#2E3742")

    # Drop the pawn so the top of its cap cone lands on the seat plane (z = 0).
    pawn_height = dims.PIECES["pawn"][0]
    hanging_pawn = bd.Pos(0, 0, -(pawn_height - dims.CAP_FLAT_HEIGHT)) * pawn()
    hanging_pawn.label = "pawn"
    hanging_pawn.color = srgb("#E8DCC4")

    return bd.Compound(children=[claw_body, gear, jaw_a, jaw_b, servo, hanging_pawn], label="claw_assembly")


if __name__ == "__main__":
    claw_assembly()
