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

# Outer ring contact: an M10 brass flat washer (McMaster 98691A118). These are
# the standard M10 sizes, so measure one with calipers when they arrive.
WASHER_OD = 20.0
WASHER_ID = 10.5
WASHER_THICKNESS = 2.0
METAL_PROUD = 0.3  # how far the metal sticks out below the plastic

# Center contact: an M3 hex-head bolt (McMaster 91280A104) held by a nut. The
# flat top of the head faces down and is the contact.
M3_CLEARANCE = 3.4
M3_HEAD_FLATS = 5.5
M3_HEAD_CORNERS = 6.0  # the corners are chamfered, so it's a little under a sharp hexagon
M3_HEAD_HEIGHT = 2.0
M3_NUT_FLATS = 5.5
M3_NUT_CORNERS = 6.35
M3_NUT_THICKNESS = 2.4
SCREW_LENGTH = 8.0  # under the head. Anything from 6 to 16 fits

# The contact plug is a small printed insulator that sits in the washer's hole
# and holds the bolt, so the two contacts never touch each other. Its flange is
# a bar instead of a disc so the magnets fit on either side of it.
PLUG_RADIUS = (WASHER_ID - FIT_SLIP) / 2
PLUG_FLANGE_LENGTH = 16.0  # along X, so it overlaps the washer by 2.75 at each end
PLUG_FLANGE_WIDTH = M3_NUT_FLATS  # along Y, the same as the nut that sits on it
PLUG_FLANGE_THICKNESS = 0.9
FLANGE_POCKET_DEPTH = 1.0

# Two disc magnets in each piece pull it down onto the board. They sit just
# above the brass washer, one on each side of the nut. Brass isn't magnetic,
# so they grab a steel washer buried under each square instead (see below).
# KJ Magnetics D52: 5/16" x 1/8". The bigger D62 doesn't fit in the pawn.
PIECE_MAGNET_DIA = 7.94
PIECE_MAGNET_THICKNESS = 3.175
MAGNET_FLOOR = 0.45  # plastic between the washer and the magnets
MAGNET_ROOF = 0.6  # plastic printed over the magnets after you drop them in
MAGNET_WALL = 0.8  # plastic between each magnet and the nut

# Room for the resistor above the magnets. A 1/4 W resistor is about 6.3 x 2.4.
RESISTOR_CAVITY_RADIUS = 6.0
RESISTOR_CAVITY_HEIGHT = 10.0
LEAD_SLOT_WIDTH = 1.6
LEAD_SLOT_REACH = 9.6  # the resistor lead comes down here and gets soldered to the washer

# --- Board pads ----------------------------------------------------------------

# Copper tape pads on each square. With these sizes a piece still reads
# correctly when it's up to 3 mm off center. checks/fit_check.py proves it.
# (It was 4 mm with the bigger M12 washer.)
PLACEMENT_TOLERANCE = 3.0
PAD_CENTER_RADIUS = 1.5
PAD_RING_INNER = 6.5
PAD_RING_OUTER = 13.0

# A steel washer buried under each square is what the piece magnets grab. It's
# centered, so it also pulls a piece toward the middle of its square. Plain
# zinc-plated steel M10 washers (DIN 125), the same size as the brass ones.
TARGET_WASHER_OD = 20.0
TARGET_WASHER_ID = 10.5
TARGET_WASHER_THICKNESS = 2.0
TARGET_SKIN = 1.0  # plastic between the steel washer and the pads. Thicker means weaker pull

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
FOOT_HEIGHT = 7.0  # the round foot at the bottom of every piece. Tall enough to wrap around the magnets
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

# --- Gantry ----------------------------------------------------------------------

# Board coordinates: x = y = 0 is the center of the board and z = 0 is the top of
# the pads. Squares reach +-175. The captured pieces go in two extra columns on
# each side of the board, at x = +-225 and +-275, so the claw needs to reach:
CLAW_REACH_X = 275.0
CLAW_REACH_Y = 175.0
CAPTURE_COLUMNS_X = (225.0, 275.0)
BOARD_THICKNESS = 10.0  # the printed tiles: 6 of rails plus a 4 mm plate

# The frame is the aluminum extrusion we already have. Two 600 mm 3030 bars are
# the runways, held up at the corners by four 2525 posts. One 450 mm 3030 bar
# is the bridge. It rides along the runways in X and carries the claw in Y.
# Check the slot widths: the hardware below assumes an 8 mm slot on the 3030
# (M6 tee nuts) and a 6 mm slot on the 2525 (M5 tee nuts).
RUNWAY_PROFILE = 30.0
RUNWAY_LENGTH = 600.0
BRIDGE_LENGTH = 450.0
POST_PROFILE = 25.0
M6_CLEARANCE = 6.6
M5_CLEARANCE = 5.5

# The runways sit over the edges of the board. They're high enough that the
# claw, even lifted all the way with a king hanging from it, passes under them.
RUNWAY_Y = BRIDGE_LENGTH / 2 - RUNWAY_PROFILE / 2  # 210, so the bridge ends sit right over them
RUNWAY_BOTTOM_Z = 230.0
POST_GAP = 4.5  # posts stand this far outside the edge of the board, so the post feet clear it too

# The claw hangs off the side of the bridge, so it's this far from the bridge's
# center line in X. This is a guess until the Z carriage is designed.
CLAW_OFFSET_X = 60.0

# MGN12 linear rails bolted on top of the runways and on the side of the bridge.
# The wheels for 20 mm V-slot don't fit 3030, and these work on any slot type.
# The C carriage is shorter, which is what lets a 600 mm rail cover 550 of travel.
MGN12_RAIL_WIDTH = 12.0
MGN12_RAIL_HEIGHT = 8.0
MGN12_HEIGHT = 13.0  # bottom of the rail to the top of the carriage
MGN12_CARRIAGE_WIDTH = 27.0
MGN12C_LENGTH = 34.7
MGN12C_HOLES = (15.0, 20.0)  # along the rail, across the rail (M3)
MGN12H_LENGTH = 45.4
X_RAIL_LENGTH = RUNWAY_LENGTH
Y_RAIL_LENGTH = BRIDGE_LENGTH

# NEMA 17 motors (StepperOnline 17HE15-1504S) and GT2 belt on 20-tooth pulleys.
NEMA17_SIZE = 42.3
NEMA17_LENGTH = 38.0
NEMA17_HOLE_SPACING = 31.0
NEMA17_BOSS_DIA = 22.0
NEMA17_SHAFT_LENGTH = 24.0
GT2_PITCH = 2.0
PULLEY_TEETH = 20
PULLEY_PITCH_RADIUS = GT2_PITCH * PULLEY_TEETH / (2 * 3.141592653589793)  # 6.37
BELT_WIDTH = 6.0
BELT_THICKNESS = 1.4
