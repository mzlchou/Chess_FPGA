# Loopback board test

First test on real hardware: the CPU sends a buffer through the AXI DMA, `axis_test` adds 1 to every 64-bit beat, and the CPU checks every value that comes back. If this passes, the whole CPU → DMA → FPGA → DDR path works.

| File | What |
| --- | --- |
| `loopback_pynq.py` | Test 1: PYNQ drives the DMA. Run this first. |
| `axi_dma.hpp` | Our C++ AXI DMA driver (simple mode, polling) |
| `dma_lib.cpp`, `Makefile` | Builds the driver as `libaxidma.so` for Python to call |
| `loopback_cpp.py` | Test 2: same test, but our C++ driver drives the DMA |

Run test 1 before test 2. If test 1 passes and test 2 fails, the bug is in our driver, not the hardware.

## 1. Build the bitstream (your PC, Vivado 2023.2)

1. `source C:/chess/accelerator/scripts/create_project.tcl`
2. Flow Navigator → **Generate Bitstream** (runs synthesis and implementation first).
3. Collect the two files PYNQ needs. They must have the same name. In the Tcl Console:
   ```tcl
   set p C:/chess/accelerator/vivado/chess_accel
   file copy -force $p/chess_accel.runs/impl_1/design_1_wrapper.bit C:/chess/loopback.bit
   file copy -force $p/chess_accel.gen/sources_1/bd/design_1/hw_handoff/design_1.hwh C:/chess/loopback.hwh
   ```
   `.bit` is the FPGA design. `.hwh` is the map PYNQ reads to find `axi_dma_0` and its address.

## 2. Set up the Kria (once)

1. Flash the Kria Ubuntu image to a microSD card, boot, and log in (`ubuntu` / `ubuntu`).
2. Install PYNQ: follow the README at https://github.com/Xilinx/Kria-PYNQ (check which Ubuntu version it supports before flashing).

## 3. Run

Copy this folder and the two files onto the board:

```bash
scp -r accelerator/sw/loopback ubuntu@<board-ip>:~/
scp loopback.bit loopback.hwh ubuntu@<board-ip>:~/loopback/
```

On the board:

```bash
cd ~/loopback
source /etc/profile.d/pynq_venv.sh      # PYNQ's Python environment (installed by Kria-PYNQ)
sudo -E python3 loopback_pynq.py        # test 1
make                                    # build libaxidma.so
sudo -E python3 loopback_cpp.py         # test 2
```

Both should end with `PASS`. Root is needed for both: PYNQ to load the bitstream, the C++ driver to open `/dev/mem`.

## If it fails

| Symptom | Likely cause |
| --- | --- |
| `Overlay` can't find the `.hwh`, or no `axi_dma_0` | `.bit` and `.hwh` not in the same folder with the same base name |
| Test 1 hangs in `wait()` | The stream never finished: check `tlast` reaches the DMA. Ctrl-C, then look at `dma.register_map` |
| Test 2 says `timed out` | Same as above. Status bit 0x1000 = done, 0x0001 = halted, 0x0070 = error |
| Test 2 says `DMA error` with 0x0040 (decode error) | A buffer address the DMA can't reach. The DMA only maps DDR below 2 GB (`0x0000_0000`–`0x7FFF_FFFF`) |
| Wrong values, but no error | Cache problem (test 2: check `flush`/`invalidate`) or a byte-order mixup |
| Board freezes when the script starts | The DMA registers were touched before the bitstream was loaded |
