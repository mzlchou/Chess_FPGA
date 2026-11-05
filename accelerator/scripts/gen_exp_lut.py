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
"""

import argparse
import math
from pathlib import Path

def generate_lut(scale: float, depth: int, out_path: Path):
    """
    Function: generate_lut
    Purpose: Create a LUT for exp(x), ranging from exp(-512 * S) to exp(0)
    
    Parameters: 
        Scale: The max magnitude the NN ranges in weight values. In this instance, 496 was given,
               divided by 2^15 
        Depth: Number of Entries in LUT (512)
        Out_path: Path to output .mem file
    
    Returns: 
        None
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        # Define the Header Value for the LUT in .mem format
        f.write(f"// {depth}-entry LUT for exp(-k * scale)\n")
        f.write(f"// Scale: {scale:.10f} (from centered score range ~496 / 32768)\n")
        f.write("// Format: 16-bit hex, Unsigned Q0.16 (0xFFFF = 1.0)\n")
        f.write("// Index k = (x_max - x), where k in [0, depth - 1]\n")
        
        # Let k be x_max - x. Then k must be nonnegative
        for k in range(depth):
            # exp() calculation
            val_real = math.exp(-k * scale)

            # Convert to Q0.16 format, all 16 bits to Fractional Value
            val_q16 = int(round(val_real * 65535.0))

            # Clip Values, ensures that 0 <= val_q16 <= 0xFFFF
            val_q16 = min(max(val_q16, 0), 0xFFFF)

            # Convert to Hex
            f.write(f"{val_q16:04X}\n")

def main():
    parser = argparse.ArgumentParser(description="Generate 1KB exp() LUT for Softmax")
    parser.add_argument("--scale", type=float, default=496.0 / 32768.0,
                        help="Scale per LSB (default: 496.0/32768.0  ~0.01514)")
    parser.add_argument("--depth", type=int, default=512,
                        help="Number of LUT entries (default: 512, fits in 1KB)")
    parser.add_argument("--out", type=str, default=None,
                        help="Output .mem file path")
    args = parser.parse_args()

    if args.out is None:
        out_file = Path(__file__).resolve().parent.parent / "rtl" / "sfu" / "exp_lut.mem"
    else:
        out_file = Path(args.out)

    generate_lut(args.scale, args.depth, out_file)


if __name__ == "__main__":
    main()
