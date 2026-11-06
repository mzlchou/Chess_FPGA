// =============================================================================
// axi_dma.hpp
// Minimal driver for the Xilinx AXI DMA in simple (direct register) mode.
// Maps the DMA's registers from /dev/mem and runs one transfer at a time,
// polling for completion. Register map: Xilinx PG021, "Direct Register Mode".
// Owner: Paul
//
// Needs root (for /dev/mem). Buffers must be physically contiguous DDR that
// the caller owns, e.g. from pynq.allocate or u-dma-buf.
// =============================================================================
#pragma once

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>

#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

class AxiDma {
 public:
  // Register offsets in bytes
  static constexpr size_t MM2S_DMACR  = 0x00;  // send: control
  static constexpr size_t MM2S_DMASR  = 0x04;  // send: status
  static constexpr size_t MM2S_SA     = 0x18;  // send: source address, low 32 bits
  static constexpr size_t MM2S_SA_MSB = 0x1C;  // send: source address, high 32 bits
  static constexpr size_t MM2S_LENGTH = 0x28;  // send: bytes; writing it starts the send
  static constexpr size_t S2MM_DMACR  = 0x30;  // receive: control
  static constexpr size_t S2MM_DMASR  = 0x34;  // receive: status
  static constexpr size_t S2MM_DA     = 0x48;  // receive: destination address, low 32 bits
  static constexpr size_t S2MM_DA_MSB = 0x4C;  // receive: destination address, high 32 bits
  static constexpr size_t S2MM_LENGTH = 0x58;  // receive: max bytes; reads back bytes received

  // Control register bits
  static constexpr uint32_t CR_RUN   = 1u << 0;
  static constexpr uint32_t CR_RESET = 1u << 2;

  // Status register bits
  static constexpr uint32_t SR_HALTED = 1u << 0;
  static constexpr uint32_t SR_ERRORS = 0x70;     // bits 4-6: internal, slave, decode error
  static constexpr uint32_t SR_IOC    = 1u << 12; // transfer done; write 1 to clear

  // 0xA0000000 / 64 KB: from assign_bd_address in bd/loopback.tcl
  explicit AxiDma(uint64_t base = 0xA0000000, size_t span = 0x10000) : span_(span) {
    fd_ = open("/dev/mem", O_RDWR | O_SYNC);
    if (fd_ < 0) throw std::runtime_error("open /dev/mem failed (run as root)");

    void* p = mmap(nullptr, span_, PROT_READ | PROT_WRITE, MAP_SHARED, fd_, base);
    if (p == MAP_FAILED) {
      close(fd_);
      throw std::runtime_error("mmap of DMA registers failed");
    }
    regs_ = static_cast<volatile uint32_t*>(p);
    reset();
  }

  ~AxiDma() {
    munmap(const_cast<uint32_t*>(regs_), span_);
    close(fd_);
  }

  // Owns a hardware mapping: never copy it.
  AxiDma(const AxiDma&) = delete;
  AxiDma& operator=(const AxiDma&) = delete;

  // Soft reset (resets both channels), then set both channels running.
  void reset() {
    write(MM2S_DMACR, CR_RESET);
    auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(100);
    while (read(MM2S_DMACR) & CR_RESET) {
      if (std::chrono::steady_clock::now() > deadline)
        throw std::runtime_error("DMA reset timed out (is the bitstream loaded?)");
    }
    write(MM2S_DMACR, CR_RUN);
    write(S2MM_DMACR, CR_RUN);
  }

  // Send src_bytes from src_phys through the stream, receive up to dst_bytes
  // into dst_phys, and wait for both. Returns the bytes actually received.
  uint32_t transfer(uint64_t src_phys, uint32_t src_bytes,
                    uint64_t dst_phys, uint32_t dst_bytes,
                    std::chrono::milliseconds timeout = std::chrono::milliseconds(1000)) {
    write(MM2S_DMASR, SR_IOC);  // clear old done flags
    write(S2MM_DMASR, SR_IOC);

    // Receive side first, so no output beat arrives before it is armed.
    write(S2MM_DA,     static_cast<uint32_t>(dst_phys));
    write(S2MM_DA_MSB, static_cast<uint32_t>(dst_phys >> 32));
    write(S2MM_LENGTH, dst_bytes);

    write(MM2S_SA,     static_cast<uint32_t>(src_phys));
    write(MM2S_SA_MSB, static_cast<uint32_t>(src_phys >> 32));
    write(MM2S_LENGTH, src_bytes);  // go

    wait_done(MM2S_DMASR, timeout, "send (MM2S)");
    wait_done(S2MM_DMASR, timeout, "receive (S2MM)");
    return read(S2MM_LENGTH);
  }

  uint32_t read(size_t off) const        { return regs_[off / 4]; }
  void     write(size_t off, uint32_t v) { regs_[off / 4] = v; }

 private:
  void wait_done(size_t sr, std::chrono::milliseconds timeout, const char* name) {
    auto deadline = std::chrono::steady_clock::now() + timeout;
    while (true) {
      uint32_t s = read(sr);
      if (s & SR_ERRORS) throw std::runtime_error(std::string(name) + " DMA error, status=" + hex(s));
      if (s & SR_IOC) return;
      if (std::chrono::steady_clock::now() > deadline)
        throw std::runtime_error(std::string(name) + " timed out, status=" + hex(s));
    }
  }

  static std::string hex(uint32_t v) {
    char buf[16];
    snprintf(buf, sizeof buf, "0x%08x", v);
    return buf;
  }

  int                fd_   = -1;
  size_t             span_ = 0;
  volatile uint32_t* regs_ = nullptr;  // volatile: every access goes to the hardware
};
