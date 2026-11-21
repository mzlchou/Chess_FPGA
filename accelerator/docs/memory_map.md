# Memory map

v0.1, 2026-11-21. Every memory in the accelerator and what it costs.
Unit costs are measured (synth_log.md, Nov 21). Bank sizes are for d = 128, 4 heads,
MLP 256, 16-bit activations (N11), and are estimates until Matthew freezes the model.
Each bank gets one line; replace "est" with a synthesis number as each bank is built.

## Measured unit costs (mem_bank, out of context, 100 MHz, all met timing)

| Word | Depth | Read ports | Style | Cost |
| --- | --- | --- | --- | --- |
| 1,024 b | 64 | 1 | LUTRAM | 1,172 LUTRAM + 2,050 FF |
| 1,024 b | 128 | 2 | LUTRAM | 4,688 LUTRAM + 1,027 LUT + 6,150 FF |
| 1,024 b | 128 | 1 | BRAM | 14.5 BRAM36 |
| 1,024 b | 512 | 2 | BRAM | 29 BRAM36 (copied for the 2nd read port) |
| 1,024 b | 128 | 1 | URAM | 15 URAM |
| 1,024 b | 4,096 | 1 | URAM | 15 URAM |

Rules that follow: BRAM and URAM cost is set by width (about 1 BRAM36 per 72 bits, 1 URAM per
72 bits) up to 512 / 4,096 deep; a 2nd read port doubles them. LUTRAM cost grows with depth.

## Banks (v0 plan)

| Bank | Holds | Lane | Word | Depth | Rd | Style | Cost | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| in | 352 input features | 8 | 512 | 352 | 1 | BRAM | ~7.5 BRAM36 | est |
| x | residual stream X | 16 | 1,024 | 128 | 2 | LUTRAM | 5,715 LUT | measured config |
| q | Q | 16 | 1,024 | 128 | 1 | LUTRAM | ~2.9K LUT | est |
| k | K | 16 | 1,024 | 128 | 1 | LUTRAM | ~2.9K LUT | est |
| v | V, split 8 ways for A.V (P2.4) | 16 | 1,024 | 8 x 16 | 1 each | LUTRAM | ~9.4K LUT | est |
| s | scores, one head | 40 | 2,560 | 64 | 1 | LUTRAM | ~2.9K LUT | est |
| a | softmax probs, one head | 16 | 1,024 | 64 | 1 | LUTRAM | ~1.2K LUT | est |
| g | GAB bias, one head | 16 | 1,024 | 64 | 1 | LUTRAM | ~1.2K LUT | est |
| o | attention / branch output | 16 | 1,024 | 128 | 1 | LUTRAM | ~2.9K LUT | est |
| h | MLP hidden | 16 | 1,024 | 256 | 1 | BRAM | 14.5 BRAM36 | measured config |
| weights | all weights, INT8 | 8 | 64 | 200K | 1 | URAM | 49 URAM + 360 LUT | measured (weight_mem, Nov 21) |
| exp ROM | softmax table | 16 | 16 | 512-1,024 | 2 | BRAM | 0.5-1 BRAM36 | est |

## Totals (v0, mostly estimates)

| Resource | Used | Device | Share |
| --- | --- | --- | --- |
| LUTRAM | ~29K LUTs | 57,600 LUTs usable as memory | ~50% |
| BRAM36 | ~23 | 144 | ~16% |
| URAM | 49 (measured) | 64 | 77% |

## Open

- URAM is the tight one. weight_mem synthesis gives the real count. If it is over ~55, move
  the GAB templates (262K weights) to BRAM, where there is room.
- LUTRAM at ~50% is the next tightest. BRAM has ~120 spare: moving q, k or o to BRAM costs
  14.5 BRAM36 each and frees ~2.9K LUTs each. Decide when mme and the SFUs have LUT numbers.
- The 8-way V split for A.V is the most expensive bank in LUTRAM and is not designed yet (P2.4).
- BRAM read-during-write: synthesis picked READ_FIRST on the write port. Either confirm the old
  word with a post-synthesis simulation, or have mme never read an address in the cycle it is
  written.
