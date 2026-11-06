# =============================================================================
# loopback_pynq.py
# Board test for the loopback block design (Zynq + DMA + axis_test).
# Sends a buffer through the DMA, axis_test adds 1 to every 64-bit beat,
# and checks every value that comes back. PYNQ does all the driver work.
# Owner: Paul
#
# Run on the Kria, with loopback.bit and loopback.hwh in this folder:
#     sudo -E python3 loopback_pynq.py
# =============================================================================
import sys
import time

import numpy as np
from pynq import Overlay, allocate

N = 1024  # 64-bit beats per transfer (8 KB, about one board position)

# ---- Load the bitstream -----------------------------------------------------
# Finds loopback.hwh next to the .bit and uses it to name the IP blocks.
ol = Overlay("loopback.bit")
dma = ol.axi_dma_0

# ---- DMA-safe buffers in DDR ------------------------------------------------
inp = allocate(shape=(N,), dtype=np.uint64)
out = allocate(shape=(N,), dtype=np.uint64)

rng = np.random.default_rng(0)
inp[:] = rng.integers(0, 2**63, size=N, dtype=np.uint64)
inp[0] = 0                      # easy one to read
inp[1] = 2**64 - 1              # all ones: should wrap around to 0
out[:] = 0
expect = np.array(inp) + np.uint64(1)  # wraps on overflow, same as the hardware

# ---- One transfer -----------------------------------------------------------
t0 = time.perf_counter()
dma.recvchannel.transfer(out)   # arm the receive side first
dma.sendchannel.transfer(inp)   # this starts the send
dma.sendchannel.wait()
dma.recvchannel.wait()
t1 = time.perf_counter()

# ---- Check ------------------------------------------------------------------
bad = np.flatnonzero(out != expect)
print(f"first beats: in={inp[:4]}  out={out[:4]}")
print(f"{N} beats in {(t1 - t0) * 1e6:.0f} us (includes Python overhead)")
if len(bad):
    for i in bad[:10]:
        print(f"  MISMATCH beat {i}: in={inp[i]:#x} out={out[i]:#x} expect={expect[i]:#x}")
    print(f"FAIL: {len(bad)} of {N} beats wrong")
else:
    print("PASS")

inp.freebuffer()
out.freebuffer()
sys.exit(1 if len(bad) else 0)
