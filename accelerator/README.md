# Accelerator

Onboard inference accelerator for the robotic chess capstone, on the AMD Kria KR260.

## Build the Vivado project

1. Install Vivado 2023.2 with the KR260 board files.
2. Clone the repo to `C:\chess` (no spaces anywhere in the path).
3. In the Vivado Tcl Console: `source C:/chess/accelerator/scripts/create_project.tcl`

Re-run step 3 after every `git pull`. The project in `accelerator/vivado/` is generated and never committed.

## Layout

Paths are relative to `accelerator/`.

| Folder | What | Owner |
| --- | --- | --- |
| `rtl/common` | `accel_pkg.sv` (empty until the interface freeze), `axis_test.sv` | Michael |
| `rtl/core` | Compute core, memories, control registers | Michael |
| `rtl/sfu` | Numerics units | Hoang |
| `rtl/io` | Stream adapters, weight loader | Paul |
| `tb` | One self-checking testbench per module | Module owner |
| `scripts` | Project script, exporter, Python reference | Michael, Hoang |
| `bd` | Block design, exported as Tcl | Michael |
| `sw` | Runtime, driver, baselines | Paul, Jonah |
| `docs` | `numerics.md`, `bringup.md` | Hoang, Paul |
