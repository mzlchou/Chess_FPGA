// =============================================================================
// mem_bank.sv
// Generic activation memory: one write port, N_RD read ports.
// One word = one feature for all 64 squares (feature-major), so this is what
// feeds mac_array's lane input a.
// Owner:     Michael
// Latency:   RD_LAT clock cycles from re/raddr to rdata, the same for every STYLE
// Primitive: STYLE 0 = LUTRAM (distributed), 1 = BRAM (RAMB36/18), 2 = URAM288
// Part of:   mme
//
// Rules:
// - Read during a write to the same address returns the OLD word.
// - Contents are not reset. Only rvalid is reset.
// - rdata holds its value while re = 0 (every read stage has an enable).
// - After a reset, rdata is undefined until the first new read comes out.
// =============================================================================
`timescale 1ns / 1ps

module mem_bank
  import accel_pkg::*;
#(
  parameter int WORD_W = ACT_WORD_W,          // bits per word (64 lanes x lane width)
  parameter int DEPTH  = 128,                 // number of words
  parameter int N_RD   = 1,                   // read ports: 1 or 2
  parameter int RD_LAT = accel_pkg::RD_LAT,   // read latency in cycles, >= 1
  parameter int STYLE  = 0,                   // 0 LUTRAM, 1 BRAM, 2 URAM
  parameter int AW     = (DEPTH > 1) ? $clog2(DEPTH) : 1   // derived, don't override
)(
  input  logic clk,
  input  logic rst_n,

  // write port
  input  logic                         we,
  input  logic [AW-1:0]                waddr,
  input  logic [WORD_W-1:0]            wdata,

  // read ports
  input  logic [N_RD-1:0]              re,
  input  logic [N_RD-1:0][AW-1:0]      raddr,
  output logic [N_RD-1:0][WORD_W-1:0]  rdata,
  output logic [N_RD-1:0]              rvalid
);

  initial begin
    if (N_RD < 1 || N_RD > 2 || RD_LAT < 1 || STYLE < 0 || STYLE > 2)
      $error("mem_bank: N_RD=%0d RD_LAT=%0d STYLE=%0d not supported", N_RD, RD_LAT, STYLE);
  end

  // first read register, one per port (filled by the memory below)
  logic [WORD_W-1:0] q0 [N_RD];

  // ---------------------------------------------------------------------------
  // The memory. Same code three times so each copy can carry its own ram_style.
  // Reads and the write happen on the same edge with nonblocking assignments,
  // so a read sees mem before this edge's write: same address returns the old word.
  // ---------------------------------------------------------------------------
  if (STYLE == 0) begin : g_lutram
    (* ram_style = "distributed" *) logic [WORD_W-1:0] mem [DEPTH];
    always_ff @(posedge clk)
      if (we) mem[waddr] <= wdata;
    for (genvar p = 0; p < N_RD; p++) begin : g_rd
      always_ff @(posedge clk)
        if (re[p]) q0[p] <= mem[raddr[p]];
    end
  end else if (STYLE == 1) begin : g_bram
    (* ram_style = "block" *) logic [WORD_W-1:0] mem [DEPTH];
    always_ff @(posedge clk)
      if (we) mem[waddr] <= wdata;
    for (genvar p = 0; p < N_RD; p++) begin : g_rd
      always_ff @(posedge clk)
        if (re[p]) q0[p] <= mem[raddr[p]];
    end
  end else begin : g_uram
    (* ram_style = "ultra" *) logic [WORD_W-1:0] mem [DEPTH];
    always_ff @(posedge clk)
      if (we) mem[waddr] <= wdata;
    for (genvar p = 0; p < N_RD; p++) begin : g_rd
      always_ff @(posedge clk)
        if (re[p]) q0[p] <= mem[raddr[p]];
    end
  end

  // ---------------------------------------------------------------------------
  // Extra read pipeline: RD_LAT - 1 more registers after q0, so every STYLE has
  // the same latency (and BRAM/URAM can absorb them as output registers).
  // rvalid follows re through the same number of stages.
  // ---------------------------------------------------------------------------
  for (genvar p = 0; p < N_RD; p++) begin : g_port
    logic v [RD_LAT];      // rvalid pipeline

    always_ff @(posedge clk) begin
      if (!rst_n) begin
        for (int i = 0; i < RD_LAT; i++) v[i] <= 1'b0;
      end else begin
        v[0] <= re[p];
        for (int i = 1; i < RD_LAT; i++) v[i] <= v[i-1];
      end
    end
    assign rvalid[p] = v[RD_LAT-1];

    if (RD_LAT == 1) begin : g_lat1
      assign rdata[p] = q0[p];
    end else begin : g_latn
      logic [WORD_W-1:0] qp [RD_LAT-1];   // data pipeline after q0, not reset
      // each stage only moves when the stage before it holds a read (v[i]),
      // so Vivado can absorb these into the URAM cascade / BRAM output registers
      always_ff @(posedge clk) begin
        if (v[0]) qp[0] <= q0[p];
        for (int i = 1; i < RD_LAT-1; i++)
          if (v[i]) qp[i] <= qp[i-1];
      end
      assign rdata[p] = qp[RD_LAT-2];
    end
  end

endmodule
