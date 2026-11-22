#!/usr/bin/env python3
"""
Generate a LUT table (1024 entries, 16-bit) (FROM MATTHEW NEWEST UPDATE)
Format: UINT16
Difference: 0 - 1023
Total BRAM Size: 1024 * 16 bits = 2 KB
"""

import math
from pathlib import Path

# CONSTANTS
LUT_ENTRY_COUNT = 1024
SCALE = 1.0 / 64.0

# Define the output .mem file logistics
output_dir = Path(__file__).resolve().parent.parent / "rtl" / "sfu"
output_dir.mkdir(parents=True, exist_ok=True)
mem_file = output_dir / "exp_lut.mem"

with open(mem_file, "w") as f:
    # This is straight from Matt's Document 
    f.write("// Table represents round(65535 * exp(-difference / 64))\n")
    for diff in range(LUT_ENTRY_COUNT):
        # Diff represents max - current value, exponent bounded between 0 - 1
        val_real = math.exp(-diff * SCALE)
        val_uint16 = int(round(val_real * 65535.0))
        val_uint16 = min(max(val_uint16, 0), 0xFFFF)
        f.write(f"{val_uint16:04X}\n")
