# Synthesis log

Out-of-context synthesis, Vivado 2023.2, `xck26-sfvc784-2LV-c`, 10 ns clock
(`create_clock -period 10` after `synth_design -mode out_of_context`).
WNS is the post-synthesis estimate with nothing placed. Re-check after place and route.

Commit column: the commit the RTL was taken from. `+attrs` means `pe.sv` also had the
uncommitted `use_dsp` / `keep` change that was committed right after.

| Date | Commit | Module | Parameters | LUT | LUTRAM | FF | DSP | BRAM | URAM | WNS (ns) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-18 | 8bfc0c7 | `pe` | A_W 17, W_W 16, ACC_W 40 (defaults) | 2 | 0 | 4 | 1 | 0 | 0 | not run | A/B, M, P registers packed into the DSP; no LUT multiplier |
| 2026-11-18 | 8bfc0c7 | `mac_array` | 64 x 8, 17/16/40 | 2 | 0 | 2,129 | 512 | 0 | 0 | +7.011 | Worst path: one merged `clear_2` driving 512 DSPs (fo=512) |
| 2026-11-18 | 8bfc0c7 | `mac_array` | 64 x 16, 17/16/40 | 2 | 0 | 3,062 | 1,024 | 0 | 0 | +6.438 | Same merged `clear_2`, fo=1,024. 82% of DSPs |
| 2026-11-18 | 8bfc0c7 | `mac_array` | 64 x 8, 8/8/32 | 48,129 | 0 | 26,174 | 0 | 0 | 0 | +7.894 | Vivado built the 8 x 8 MACs from LUTs and CARRY8 (6,144) |
| 2026-11-18 | 8bfc0c7+attrs | `mac_array` | 64 x 8, 8/8/32 | 513 | 0 | 4,352 | 512 | 0 | 0 | +8.482 | `use_dsp` puts 8-bit MACs in DSPs; `keep` gives each pe its own `clear_2` (fo=1) |
| 2026-11-18 | 8bfc0c7+attrs | `mac_array` | 64 x 8, 17/16/40 | 513 | 0 | 4,136 | 512 | 0 | 0 | +8.482 | Same as above at MAC widths |

## Findings

- One DSP48E2 per `pe` at every width tested, once `use_dsp` is set.
- At 64 x 8, 8-bit and 16-bit operands cost the same in the array: 512 DSPs, 513 LUTs,
  about 4K FFs, same timing. The cost of 16-bit activations is memory width, not compute.
- COLS = 16 uses 82% of DSPs in the array alone, leaving 224 for `requant` and the
  special-function units. COLS stays at 8.
