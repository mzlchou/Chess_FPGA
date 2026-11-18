#!/usr/bin/env python3
"""
Generate a 512-entry x 16-bit exp() LUT for Softmax attention scores.

Numerical Specifications (aligned with ML team findings):
- Centered attention score dynamic range: ~496.0
- INT16 scale factor: S = 496.0 / 32768.0 = 0.01513671875 per LSB
- Non-negative difference: delta = (x_max - x) >= 0 (integer difference code)
- Table maps: index k in [0, 511] -> round(exp(-k * S) * 65535)
- For delta >= 512: exp(-512 * S) <= 0.00043 (< 29/65535), safely clipped to 0
- Size: 512 x 16 bits = 1024 bytes (1 KB)
- Check the committed .mem still matches: python scripts/ref/gen_exp_lut.py --check
"""

import argparse
import math
import sys
from pathlib import Path

def generate_lut(scale: float, depth: int) -> str:
    """
    Function: generate_lut
    Purpose: Create a LUT for exp(x), ranging from exp(-512 * S) to exp(0)
    
    Parameters: 
        Scale: The max magnitude the NN ranges in weight values. In this instance, 496 was given,
               divided by 2^15 
        Depth: Number of Entries in LUT (512)
    
    Returns: 
        The .mem file contents as one string (header lines, then one hex word per line)
    """
    lines = []
    # Define the Header Value for the LUT in .mem format
    lines.append(f"// {depth}-entry LUT for exp(-k * scale)")
    lines.append(f"// Scale: {scale:.10f} (from centered score range ~496 / 32768)")
    lines.append("// Format: 16-bit hex, Unsigned Q0.16 (0xFFFF = 1.0)")
    lines.append("// Index k = (x_max - x), where k in [0, depth-1]")

    # Let k be x_max - x. Then k must be nonnegative
    for k in range(depth):
        # exp() calculation
        val_real = math.exp(-k * scale)

        # Convert to Q0.16 format, all 16 bits to Fractional Value
        val_q16 = int(round(val_real * 65535.0))

        # Clip Values, ensures that 0 <= val_q16 <= 0xFFFF
        val_q16 = min(max(val_q16, 0), 0xFFFF)

        # Convert to Hex
        lines.append(f"{val_q16:04X}")
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser(description="Generate 1KB exp() LUT for Softmax")
    parser.add_argument("--scale", type=float, default=496.0 / 32768.0,
                        help="Scale per LSB (default: 496.0/32768.0  ~0.01514)")
    parser.add_argument("--depth", type=int, default=512,
                        help="Number of LUT entries (default: 512, fits in 1KB)")
    parser.add_argument("--out", type=str, default=None,
                        help="Output .mem file path (default: rtl/sfu/exp_lut.mem)")
    parser.add_argument("--check", action="store_true",
                        help="Do not write: exit 1 if the file differs from what this script generates")
    args = parser.parse_args()

    # moved to scripts/ref/, so accelerator/ is now 2 folders up
    if args.out is None:
        out_file = Path(__file__).resolve().parents[2] / "rtl" / "sfu" / "exp_lut.mem"
    else:
        out_file = Path(args.out)

    text = generate_lut(args.scale, args.depth)

    if args.check:
        # ignore CRLF vs LF (git on windows)
        current = out_file.read_text().replace("\r\n", "\n") if out_file.exists() else None
        if current == text:
            print(f"OK: {out_file} matches the generator")
            sys.exit(0)
        print(f"MISMATCH: {out_file} differs from the generator. Regenerate it or fix the script.")
        sys.exit(1)

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w") as f:
        f.write(text)


if __name__ == "__main__":
    main()
