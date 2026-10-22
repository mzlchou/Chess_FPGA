"""Every dimension the chess robot parts share. All values are in mm.

If you want to change a size, change it here and rebuild. Nothing else in the
project should have a magic number that another part depends on.

Two reference planes show up a lot:
  - Pieces: z = 0 is the contact plane, the bottom face of the steel washer
    and the center screw head. The plastic starts a little above it so only
    metal ever touches the board.
  - Claw: z = 0 is the seat plane, where the top of a piece's cap cone sits
    when the piece is hanging in the claw.
"""

# --- Board -------------------------------------------------------------------

SQUARE = 50.0  # FIDE allows 50 to 65. We went small to keep the gantry small.
BOARD_BORDER = 25.0
BOARD_SIZE = 8 * SQUARE + 2 * BOARD_BORDER  # 450

# --- Printing ----------------------------------------------------------------

FIT_SLIP = 0.3  # extra diameter so a part drops into its pocket on an FDM print

# --- Contacts on the bottom of each piece ------------------------------------

# Outer ring contact: a plain M12 washer (DIN 125). It also adds a bit of weight.
WASHER_OD = 24.0
WASHER_ID = 13.0
WASHER_THICKNESS = 2.5
METAL_PROUD = 0.3  # how far the metal sticks out below the plastic

# Center contact: an M3 countersunk screw held by a nut.
M3_CLEARANCE = 3.4
M3_COUNTERSINK_DIA = 5.6  # a bit smaller than the head so it sits proud, then gets sanded flush
M3_NUT_FLATS = 5.5
M3_NUT_THICKNESS = 2.4
SCREW_LENGTH = 8.0

# The contact plug is a small printed insulator that sits in the washer's hole
# and holds the screw, so the two contacts never touch each other.
PLUG_RADIUS = (WASHER_ID - FIT_SLIP) / 2
PLUG_FLANGE_RADIUS = 8.0
PLUG_FLANGE_THICKNESS = 0.9
FLANGE_POCKET_RADIUS = PLUG_FLANGE_RADIUS + FIT_SLIP / 2
FLANGE_POCKET_DEPTH = 1.0

# Room for the resistor above the plug. A 1/4 W resistor is about 6.3 x 2.4.
RESISTOR_CAVITY_RADIUS = 6.0
RESISTOR_CAVITY_HEIGHT = 10.0
LEAD_SLOT_WIDTH = 1.6
LEAD_SLOT_REACH = 10.0  # the resistor lead comes down here and gets soldered to the washer

# --- Board pads ----------------------------------------------------------------

# Copper tape pads on each square. With these sizes a piece still reads
# correctly when it's up to 4 mm off center. checks/fit_check.py proves it.
PLACEMENT_TOLERANCE = 4.0
PAD_CENTER_RADIUS = 2.0
PAD_RING_INNER = 7.25
PAD_RING_OUTER = 12.0

# --- Pieces --------------------------------------------------------------------

# Heights are the FIDE tournament set scaled down to our 50 mm squares (x0.88).
PIECES = {
    #          height, base diameter
    "pawn": (45.0, 28.0),
    "rook": (50.0, 30.0),
    "knight": (55.0, 30.0),
    "bishop": (62.0, 30.0),
    "queen": (75.0, 33.0),
    "king": (83.0, 34.0),
}
FOOT_HEIGHT = 6.0  # the round foot at the bottom of every piece
STEM_START_Z = 16.0  # where the foot has tapered into the stem
STEM_RADIUS = 9.0

# Every piece has the same mushroom-shaped head so one claw can grab all of
# them. The underside of the cap is a 45 degree cone that drops into a matching
# cone on the claw jaws, which centers the piece as it's lifted.
CAP_RADIUS = 12.0
NECK_RADIUS = 5.0
CAP_CONE_HEIGHT = CAP_RADIUS - NECK_RADIUS  # 45 degrees, so it prints without support
CAP_FLAT_HEIGHT = 2.0
CAP_HEIGHT = CAP_CONE_HEIGHT + CAP_FLAT_HEIGHT
NECK_HEIGHT = 5.0  # the jaws close around this part, so the body has to stay thin here
HEAD_HEIGHT = CAP_HEIGHT + NECK_HEIGHT

# --- Claw ----------------------------------------------------------------------

# The jaws close to a fixed spot under the cap and never actually squeeze the
# neck. That leaves room for a piece that's sitting a little off center.
GRAB_TOLERANCE = 4.0
SEAT_RADIUS = NECK_RADIUS + GRAB_TOLERANCE  # inner radius of the closed jaws (9)
JAW_LIP_THICKNESS = 5.0
JAW_LIP_HALF_WIDTH = 6.0
JAW_FINGER_INNER_X = CAP_RADIUS + 5.0  # finger stays 5 mm outside the cap when closed
JAW_FINGER_THICKNESS = 4.0
JAW_FINGER_HALF_WIDTH = 8.0
JAW_STROKE = 10.0  # how far each jaw moves from closed to open
CLOSING_DROP = 5.0  # the claw closes this far below where the piece will end up seated

# Rack and pinion. The gear layer sits high enough that a cap never hits it,
# even while the claw is dropped down to close.
RACK_BOTTOM_Z = CAP_FLAT_HEIGHT + CLOSING_DROP + 2.0
RACK_THICKNESS = 6.0
GEAR_MODULE = 1.25
PINION_TEETH = 20
PINION_PITCH_RADIUS = GEAR_MODULE * PINION_TEETH / 2  # 12.5
RACK_BACKING = 5.0  # solid rack material behind the tooth roots
GUIDE_HALF_LENGTH = 15.0  # the housing guides the racks from x = -15 to 15
GUIDE_WALL_THICKNESS = 3.0
SLIDING_CLEARANCE = 0.3

# MG90S micro servo. These came off the datasheet, so measure your actual servo
# with calipers before printing the housing.
SERVO_LENGTH = 22.8
SERVO_WIDTH = 12.2
SERVO_HEIGHT = 22.7  # bottom of the case to the output face
SERVO_SHAFT_OFFSET = 5.5  # the output shaft isn't centered on the case
SERVO_FACE_TO_TAB = 4.3  # output face to the near side of the mounting tabs
SERVO_TAB_SPAN = 32.5
SERVO_TAB_THICKNESS = 2.5
SERVO_TAB_WIDTH = 5.4
SERVO_HOLE_SPACING = 27.8
HORN_CLEARANCE = 3.0  # vertical room for the horn between the pinion and the servo
HORN_SWEEP_RADIUS = 17.0
