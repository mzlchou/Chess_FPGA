// =============================================================================
// dma_lib.cpp
// Plain C interface around AxiDma, built as libaxidma.so so Python (ctypes)
// can call the C++ driver. C++ exceptions must not cross into Python, so each
// call catches them and returns an error code; dma_last_error() says why.
// Owner: Paul
// =============================================================================
#include <memory>
#include <string>

#include "axi_dma.hpp"

namespace {
std::unique_ptr<AxiDma> g_dma;
std::string             g_err;
}  // namespace

extern "C" {

// Map the DMA registers and reset it. Returns 0 on success, -1 on error.
int dma_open(uint64_t base) {
  try {
    g_dma = std::make_unique<AxiDma>(base);
    return 0;
  } catch (const std::exception& e) {
    g_err = e.what();
    return -1;
  }
}

// One transfer. Returns bytes received, or -1 on error.
long dma_transfer(uint64_t src_phys, uint32_t src_bytes,
                  uint64_t dst_phys, uint32_t dst_bytes, int timeout_ms) {
  if (!g_dma) {
    g_err = "dma_open was not called";
    return -1;
  }
  try {
    return g_dma->transfer(src_phys, src_bytes, dst_phys, dst_bytes,
                           std::chrono::milliseconds(timeout_ms));
  } catch (const std::exception& e) {
    g_err = e.what();
    return -1;
  }
}

// Read any DMA register, for debugging. Returns 0xFFFFFFFF if not open.
uint32_t dma_read_reg(uint32_t offset) {
  return g_dma ? g_dma->read(offset) : 0xFFFFFFFFu;
}

void dma_close() { g_dma.reset(); }

const char* dma_last_error() { return g_err.c_str(); }

}  // extern "C"
