# CLAUDE.md: chess accelerator (`accelerator/`)

Instructions for any Claude session working in this folder. Read all of it before writing code.
Maintained by Michael. Last updated 2026-11-13. If this file and the code disagree, report the
difference; do not silently follow either one.

## 1. First, ask who you are working with

If the person has not said, ask: "Which teammate am I working with: Michael, Hoang or Paul?"
Then stay in that person's lane.

| Person | Writes | Folders | Signs off on |
| --- | --- | --- | --- |
| Michael (lead) | Compute core, integration, block design, CPU and DPU baselines | `rtl/common`, `rtl/core`, `bd`, `scripts/*.tcl`, `sw/baselines` | Architecture, `accel_pkg`, register map, this file |
| Hoang | Special-function units, the Python integer reference, `numerics.md`, `export.py` | `rtl/sfu`, `scripts/ref`, `scripts/export.py`, `docs/numerics.md` | Every numerics convention (with Matthew) |
| Paul | Stream adapters, weight loader, PS runtime, board bring-up | `rtl/io`, `sw`, `docs/bringup.md` | Runtime API, blob loading, bring-up |
| Matthew | The model: distillation, quantization choices, training, quality | `model/` | Model structure, scales, golden data |

- Do not edit a file another person owns on your own initiative. Draft the change as a diff or a
  message for them instead, and say why.
- Shared files (`accel_pkg.sv`, `numerics.md`, the register map, this file) change only with the
  owner's approval. Show the diff first.
- Model-side work is Matthew's. Do not do it, and do not present any size, scale or range as his
  unless it is in a file he committed or in section 4 below.
- Before touching any existing file, run `git fetch --all` and `git log --follow <file>`. Older
  work may still sit on a branch (for example `sfu/exponential`), so check every branch.

## 2. What we are building

A custom RTL inference accelerator on an AMD Kria KR260 (K26 SOM, `xck26-sfvc784-2LV-c`,
Vivado 2023.2, one 100 MHz clock) that runs a distilled Maia-3 chess transformer entirely in
fabric: one inference per move, batch 1, no search. It is compared with a CPU-only path and an
AMD DPU path on latency and energy per inference.

Budget: 1,248 DSP48E2 (27 x 18 multiply, 48-bit accumulate), 144 BRAM36 (at most 72 bits
wide), 64 URAM288 (72 bits x 4,096), about 117K LUTs. A 512-bit word costs 8 BRAM36 at any
depth up to 512, so shallow wide memories go in distributed RAM.

## 3. Rules that do not bend

1. **Bit-exact.** RTL must equal the Python integer reference at every unit and every layer
   boundary, with zero differing bits. "It plays reasonable chess" proves nothing.
2. **Reference first.** For each unit write `scripts/ref/<unit>.py` (NumPy, integers only) before
   the RTL. The same file generates the test vectors.
3. **One reference.** There is exactly one implementation of each integer op. Proposed home:
   `scripts/ref/`, imported by Matthew's code in `model/`. Never write a second version of an op
   anywhere. If you find two, stop and report it.
4. **`docs/numerics.md` is the contract.** If a convention you need is not there, stop and ask
   Hoang. Do not pick one yourself, and do not copy one from a library.
5. **Never invent model numbers.** No scale, range, table size or width may come from the 23M,
   79M or 98M teachers. Those ranges do not transfer to the student.
6. **Everything is a parameter.** Modules take parameters that default to `accel_pkg` values.
   Every unit must also build and pass at a small size (for example 4 lanes, 2 columns) and at
   d = 160 with 5 heads.
7. **Honest status.** Report only what you ran: simulator name and version, check count, error
   count. Never write "verified in Vivado" or "synthesizes to N DSPs" unless a person pasted the
   Vivado output into the conversation.

## 4. Model facts (Matthew, Nov 12, 2026)

Source of truth for structure: `github.com/CSSLab/maia3` at commit `1e13597`, files
`maia3/models.py` and `maia3/model_registry.py`. Read them before writing a reference.

| Item | Value | Status |
| --- | --- | --- |
| Width, heads, MLP, blocks | d = 128, 4 heads of 32, MLP 256, 8 blocks, no sharing, about 1.6M weights | Primary candidate. Architecture freeze proposed Nov 20; final decision tentatively Dec 4 |
| Alternates to keep buildable | d = 160 with 5 heads; d = 192 with 6 heads (reference only) | Parameters, not forks |
| Input | 64 tokens x 352 features: 8 board states x 12 planes = 96, plus two 128-wide Elo embeddings | Confirmed |
| Flags | No time features, no Q/K/V/O biases, no absolute position embedding, `head_hid_dim` = d | Confirmed |
| Block | Post-norm: `x = RMSNorm(x + attn(x))`, then `x = RMSNorm(x + mlp(x))` | Confirmed |
| After last block | One LayerNorm over all tokens. The value head has its own LayerNorm on the mean-pooled vector | Confirmed |
| GAB | Mean-pool path (`gab_per_square_dim = 0`), generator size 64, intermediate 64, one 4096 x 64 template matrix shared by all blocks | Structure confirmed; scales provisional |
| Activation ranges, GELU table, norm widths | Not measured on the student yet | Open. Build as parameters |

The PS keeps a rolling history of the current position and the seven before it. The model has no
memory between calls. Short history is padded the way `maia3/dataset.py` does it, not by
repeating the current board.

## 5. Numerics contract and its status

Hoang owns this table. It is copied here so every session starts from the same place; if
`docs/numerics.md` differs, that file wins.

| # | Convention | Status |
| --- | --- | --- |
| N1 | Two's complement. `INTn` signed, `UINTn` unsigned. No floats in a reference's compute path | Agreed |
| N2 | Rounding: nearest, ties away from zero. `rnd(x, s) = (x + (1 << (s-1)) - (x < 0)) >>> s`, identity for s = 0 | Matthew's preference; Hoang to sign |
| N3 | `sat_n` clamps to [-2^(n-1), 2^(n-1) - 1]; `usat_n` to [0, 2^n - 1] | Agreed |
| N4 | Requant: `y = sat(rnd((acc >>> pre) * M, sh))`, `M` unsigned below 2^17, shifted operand at most 27 signed bits, one DSP48E2 per lane. `pre` is per column, from the exporter's bound | Form agreed by Matthew. Accuracy against his wider reference not yet measured |
| N5 | Bias is stored at accumulator scale (INT32) and added in the `mme` drain, before requant | Proposed |
| N6 | Accumulators never wrap. INT32 for INT8-weight layers (holds 16-bit activations up to K = 512). Data-by-data products with 16-bit operands on both sides need 36 to 39 bits, so accumulator width is a parameter. The exporter proves every bound | Proposed |
| N7 | Softmax per row of 64: `delta = max - score` computed at full width; `idx = min(1023, rnd(delta * M_d, sh_d))` at 1/64 nat, with delta first saturated to the requant operand width; `e = EXP_ROM[idx]` with `EXP_ROM[k] = round(65535 * exp(-k/64))`; `R = min(2^17 - 1, floor(2^32 / sum(e)))`; `p = usat_16(rnd(e * R, 16))` | Primary candidate. Matthew is rerunning it. Fallback is centered INT16, so delta width, step and table depth stay parameters |
| N8 | A committed ROM file is the definition. Its generator must reproduce it byte for byte, and a test checks that | Proposed |
| N9 | ReLU is `max(x, 0)`. GELU is a table over a clipped input | Table range and formats open |
| N10 | Norm: two passes; pass 2 recomputes `x + branch` rather than storing it wide | Widths and rsqrt routine open |
| N11 | Activations are stored as INT16 by default (the W8A16 reference). A bank drops to INT8 only when Matthew's student measurements support it | Matthew's recommendation |
| N12 | The residual sum `x + branch` is formed at INT32 after scale alignment and feeds the norm directly | Matthew's recommendation |

## 6. Architecture in one page

- **One engine.** `mme` is 64 lanes x COLS columns of `pe` (one DSP MAC each), time-multiplexed
  over every matmul. COLS = 8 for now.
- **Feature-major memory.** One word = one feature for all 64 squares; lane i is square i. A
  matmul walks down feature words. Nothing is transposed in hardware.
- **Single vectors live on lane 0** (GAB generator, value head). Other lanes must stay defined.
- **Four operand modes:** `AXW` (activation word x weight word), `AXA_QK` (QK^T and the
  policy dot), `AXA_AV` (A.V, with V in COLS banks), `GAB_MIX` (template word x one scalar).
- **The drain.** After each pass `mme` emits one column of 64 accumulators per beat. A 64-lane
  adder there adds a bias or the aligned GAB bias, and a per-lane register tracks the row
  maximum. Wide values exist only on this stream and in one score bank.
- **Special-function units** are 64 independent lanes fed word by word: `requant`, `softmax`,
  norm, `activation`. `lane_reduce` is the only cross-lane unit. Lookup tables are time-shared
  through a few ROM ports, never replicated 64 times.
- **`requant` is shared.** Its multiplier comes per column (ordinary requant) or per lane
  (softmax normalization, norm scale).

## 7. Interfaces

**Streams, everywhere:** `<name>_valid`, `<name>_ready`, `<name>_data`, `<name>_last`. Transfer
on `valid && ready`. Data holds once valid. A sender never waits for ready.

**Register map (frozen between Michael and Paul; do not change without both):**

| Offset | Name | Bits |
| --- | --- | --- |
| 0x00 | `CTRL` | 0 `start` (self-clearing), 1 `soft_reset`, 2 `irq_enable`, 3 `load_mode` |
| 0x04 | `STATUS` | 0 `idle`, 1 `busy`, 2 `done` (W1C), 3 `error`, 4 `weights_loaded` |
| 0x08 | `CONFIG` | [7:0] blocks to run, 0 = all |
| 0x0C / 0x10 / 0x14 | `EVAL_COUNT` / `BUSY_CYCLES` / `LAST_LATENCY` | Read-only counters |
| 0x18 / 0x1C | `VERSION` / `ERROR_CODE` | Git hash; 1 bad magic, 2 blob length, 3 input length |

**Blob, 64-bit beats:** beat 0 magic `0x43484553`, format version, COLS; beat 1 weight-word and
param-word counts; beat 2 GAB-word count; then weights in the order `mme` reads them, params,
GAB words.

**Per move:** the PS sends 352 feature words (feature-major), writes `start`, waits for `done`,
reads 64 policy words plus 4 promotion words and the value logits, assembles the 4,352 logits,
masks illegal moves and picks.

## 8. Layout and commands

```
rtl/common  accel_pkg.sv, shared pieces     tb/           tb_<module>.sv, one per module
rtl/core    Michael                         sim/vectors/  generated, git-ignored
rtl/sfu     Hoang                           scripts/ref/  Python integer reference
rtl/io      Paul                            sw/           runtime, driver, baselines
bd/         block design as Tcl             docs/         numerics.md, bringup.md
```

- Simulate (Icarus Verilog 12 works for the plain testbenches):
  `iverilog -g2012 -o sim.vvp rtl/common/accel_pkg.sv rtl/core/pe.sv tb/tb_pe.sv && vvp sim.vvp`
- Icarus cannot compile `string` parameters, unpacked array literals or declarations placed
  after statements. Avoid those in testbenches, or use Verilator 5 with `--binary --timing`.
- Vivado (a person runs it): `source C:/chess/accelerator/scripts/create_project.tcl` in the Tcl
  Console. It globs `rtl/*/*.sv`, `rtl/*/*.v` and `tb/*.sv`. Keep it working.
- Anything that needs Vivado: write the Tcl, give the exact line to paste, and say what to paste
  back (utilization rows, WNS, any warning that mentions DSP, RAM, ROM or latch).

## 9. RTL and testbench rules

RTL:
- SystemVerilog that Vivado 2023.2 synthesizes. `always_ff`, `always_comb`, `logic`. No
  interfaces or classes in synthesizable code. The block-design top is a plain Verilog wrapper.
- Synchronous active-low reset `rst_n`, as in `pe.sv`. Reset control and valid bits only.
- Header on every file, as in `pe.sv`: name, purpose, owner, latency, the `numerics.md` rule it
  implements, and the primitive it should infer (DSP48E2, LUTRAM, RAMB36, URAM288).
- Plain-language comments on every block. Each owner must be able to explain every line.
- No magic numbers outside `accel_pkg` and module parameters.
- Clip or saturate in the address path of a ROM, not between the ROM and its output register.

Testbenches:
- Self-checking against vectors from the Python reference, never against the same file the
  design loads.
- One final line, from the counters: `PASS: N checks, 0 errors` or `FAIL: E errors in N checks`.
  No pass message is printed unconditionally.
- Compare an output on a later clock edge than the one that produces it. `tb_pe.sv` is the
  pattern.
- Never patch the design's memory from the testbench. If a ROM file fails to load, the test fails.
- Random stalls on every input `valid` and output `ready`; one reset in mid-operation.
- Required vectors: both saturation rails at each output width, rounding ties of both signs,
  largest-magnitude operands, zeros, row maximum at lane 0 and lane 63, tied maxima, an
  all-equal row, zero variance in the norm, and at least 10,000 random words per unit.
- Run input A, then B, then A again; both A results must match.

## 10. Workflow

- Everyone works on `main`. Folder ownership (section 1) is what keeps people apart: commit
  only files in your own folders. `git pull --rebase` before you start and before you push.
- A commit for a module contains the reference, the vector generator, the RTL, the testbench and
  the doc change together. The owner of the neighboring interface reviews it.
- Review checklist: reference present and integer-only; testbench passes with counts stated;
  required vectors present; small and alternate sizes pass; every convention cited from
  `numerics.md`; header and comments complete; intended primitive named; nothing in another
  owner's files.
- End each session with: what changed, test results with counts, what is blocked and on whom,
  what needs Vivado, next step. Nothing else.
- A question for a teammate is written as a ready-to-send message: one line of context, numbered
  questions, what each answer unblocks.

## 11. Stop and ask before

- Changing the register map, blob format, stream convention or another person's ports.
- Using a numerics convention that is not in `numerics.md`.
- Changing COLS, the bank structure, the engine modes or `pe`.
- Adding CI, hooks or new top-level folders.
- Anything that contradicts this file.

## 12. Where each person starts

**Hoang**
1. `docs/numerics.md` v0 with N1 to N8, N11 and N12, and `scripts/ref/fixed.py` (`rnd`, `sat`,
   `usat`, `requant`) with tests for ties and both rails.
2. `sfu/exponential`: fix the testbench (declaration order, same-edge sampling, unconditional
   pass messages, back-door ROM load, expected values from the reference). Regenerate the table
   to N7 once N7 is signed. The current scale (496/32768) is the 79M teacher's.
3. `requant`: reference, then RTL, with the per-column and per-lane multiplier.
4. `softmax` to N7. Then, in January: add-norm, `activation` (GELU and ReLU), `lane_reduce`.
5. `export.py` and the integer reference for one whole block, checked against float.

**Paul**
1. `scripts/ref/regmap.py` as the single source for the register map, generating `regmap.svh`
   and the Python constants the runtime imports.
2. `axis_in_unpack` and `axis_out_pack` with a word-width parameter (a multiple of 64).
3. `weight_loader` and a synthetic blob from `export.py --synthetic`.
4. `sw/accel.py`: `Accel`, `load_weights`, `encode`, `infer`, `decode`, `run_golden`. `encode`
   must match the Maia-3 code: mirror for Black, eight real board states, Elo interpolation, the
   same padding. Test it on a PC against the float model before any hardware exists.
5. When the board arrives: run `sw/loopback` and record the result in `docs/bringup.md`.

**Michael**
1. `accel_pkg` v2, `pe` parameters, `mac_array`, `mem_bank`, `weight_mem`, `mme`, `csr_axil`.
2. First synthesis measurement: `mac_array` at COLS 8 and 16, and with 8-bit and 16-bit lane
   operands.
3. CPU and DPU baselines.
