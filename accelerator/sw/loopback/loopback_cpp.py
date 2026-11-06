# =============================================================================
# loopback_cpp.py
# Same test as loopback_pynq.py, but the DMA is driven by our C++ driver
# (libaxidma.so) instead of PYNQ's. PYNQ still loads the bitstream and
# allocates the DDR buffers; C++ writes the DMA registers and waits.
# Owner: Paul
#
# Run on the Kria, after `make` in this folder:
#     sudo -E python3 loopback_cpp.py
# =============================================================================
import ctypes
import os
import sys
import time

import numpy as np
from pynq import Overlay, allocate

N        = 1024        # 64-bit beats per transfer
DMA_BASE = 0xA0000000  # from bd/loopback.tcl

# ---- Load the C++ driver ----------------------------------------------------
lib = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)), "libaxidma.so"))
lib.dma_open.argtypes       = [ctypes.c_uint64]
lib.dma_open.restype        = ctypes.c_int
lib.dma_transfer.argtypes   = [ctypes.c_uint64, ctypes.c_uint32,
                               ctypes.c_uint64, ctypes.c_uint32, ctypes.c_int]
lib.dma_transfer.restype    = ctypes.c_long
lib.dma_read_reg.argtypes   = [ctypes.c_uint32]
lib.dma_read_reg.restype    = ctypes.c_uint32
lib.dma_last_error.restype  = ctypes.c_char_p

# ---- Bitstream and buffers (PYNQ) -------------------------------------------
Overlay("loopback.bit")
inp = allocate(shape=(N,), dtype=np.uint64)
out = allocate(shape=(N,), dtype=np.uint64)

rng = np.random.default_rng(0)
inp[:] = rng.integers(0, 2**63, size=N, dtype=np.uint64)
inp[0] = 0
inp[1] = 2**64 - 1
out[:] = 0
expect = np.array(inp) + np.uint64(1)

# PYNQ buffers are cached, but the DMA reads and writes DDR directly. Flush
# both before the transfer: the input so the DMA sees it, the output so no
# dirty cache line gets written back over the DMA's results later.
inp.flush()
out.flush()

# ---- One transfer (C++) -----------------------------------------------------
if lib.dma_open(DMA_BASE) != 0:
    sys.exit(f"dma_open failed: {lib.dma_last_error().decode()}")

nbytes = N * 8
t0 = time.perf_counter()
got = lib.dma_transfer(inp.physical_address, nbytes, out.physical_address, nbytes, 1000)
t1 = time.perf_counter()
if got < 0:
    print(f"transfer failed: {lib.dma_last_error().decode()}")
    print(f"  MM2S_DMASR=0x{lib.dma_read_reg(0x04):08x}  S2MM_DMASR=0x{lib.dma_read_reg(0x34):08x}")
    sys.exit(1)

out.invalidate()  # see what the DMA wrote, not old cached values

# ---- Check ------------------------------------------------------------------
bad = np.flatnonzero(out != expect)
print(f"first beats: in={inp[:4]}  out={out[:4]}")
print(f"{got} of {nbytes} bytes received in {(t1 - t0) * 1e6:.0f} us")
if len(bad):
    for i in bad[:10]:
        print(f"  MISMATCH beat {i}: in={inp[i]:#x} out={out[i]:#x} expect={expect[i]:#x}")
    print(f"FAIL: {len(bad)} of {N} beats wrong")
else:
    print("PASS")

lib.dma_close()
inp.freebuffer()
out.freebuffer()
sys.exit(1 if len(bad) else 0)
