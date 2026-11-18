// =============================================================================
// mac_array.sv
// The LANES x COLS grid of pe. One lane word (one feature for every square) goes
// across all columns; each column's operand goes down its column. After K
// enabled cycles, acc[j][s] = sum over k of a_k[s] * w_k[j].
// Owner:     Michael
// Latency:   4 clock cycles from inputs to acc (1 input register + 3 in pe)
// Numerics:  N6 (accumulators never wrap; ACC_W is a parameter)
// Primitive: LANES * COLS DSP48E2 (one per pe). The input stage is fabric FFs.
// Part of:   mme
//
// Parameters (defaults from accel_pkg):
//   LANES      rows, one per square (64)
//   COLS       output columns computed per pass (8)
//   A_W, W_W, ACC_W   passed to every pe
//   HAS_COL_A  1 = add a per-column lane word a_col and a select, for GAB_MIX.
//              0 = a_col and col_a_sel are ignored and cost nothing.
// =============================================================================
`timescale 1ns / 1ps

module mac_array
  import accel_pkg::*;
#(
  parameter int LANES     = accel_pkg::LANES,
  parameter int COLS      = accel_pkg::COLS,
  parameter int A_W       = MAC_A_W,
  parameter int W_W       = MAC_W_W,
  parameter int ACC_W     = MAC_ACC_W,
  parameter bit HAS_COL_A = 1'b0
)(
  input  logic clk,
  input  logic rst_n,

  input  logic en,                                   // 1 = every pe uses this cycle's operands
  input  logic clear,                                // 1 = every pe starts a new sum (only with en)
  input  logic [LANES-1:0][A_W-1:0]           a,     // lane word: lane s = square s, shared by all columns
  input  logic [COLS-1:0][W_W-1:0]            w,     // column operands: w[j] goes down column j
  input  logic                                col_a_sel, // HAS_COL_A only: 1 = column j uses a_col[j]
  input  logic [COLS-1:0][LANES-1:0][A_W-1:0] a_col, // HAS_COL_A only: one lane word per column

  output logic [COLS-1:0][LANES-1:0][ACC_W-1:0] acc  // acc[j][s]: column j, square s
);

  // ---------------------------------------------------------------------------
  // Input register stage.
  // Every a[s] fans out to COLS pes, every w[j] to LANES pes, and en/clear to
  // all LANES * COLS pes. One register here keeps that fan-out off the path
  // from whatever drives the array. Only en and clear are reset (CLAUDE.md 9).
  // ---------------------------------------------------------------------------
  (* max_fanout = 64 *) logic en_r, clear_r;
  logic [LANES-1:0][A_W-1:0] a_r;
  logic [COLS-1:0][W_W-1:0]  w_r;

  always_ff @(posedge clk) begin
    a_r <= a;
    w_r <= w;
    if (!rst_n) begin
      en_r    <= 1'b0;
      clear_r <= 1'b0;
    end else begin
      en_r    <= en;
      clear_r <= clear;
    end
  end

  // ---------------------------------------------------------------------------
  // Lane word seen by each column.
  // HAS_COL_A = 0: every column sees a_r.
  // HAS_COL_A = 1: column j sees a_col[j] when col_a_sel is 1, else a_r.
  // ---------------------------------------------------------------------------
  logic [COLS-1:0][LANES-1:0][A_W-1:0] a_eff;

  if (HAS_COL_A) begin : g_col_a
    logic                                sel_r;
    logic [COLS-1:0][LANES-1:0][A_W-1:0] a_col_r;

    always_ff @(posedge clk) begin
      sel_r   <= col_a_sel;
      a_col_r <= a_col;
    end

    for (genvar j = 0; j < COLS; j++) begin : g_sel
      assign a_eff[j] = sel_r ? a_col_r[j] : a_r;
    end
  end else begin : g_no_col_a
    for (genvar j = 0; j < COLS; j++) begin : g_bcast
      assign a_eff[j] = a_r;
    end
  end

  // ---------------------------------------------------------------------------
  // The grid: pe(s, j) for square s, column j.
  // ---------------------------------------------------------------------------
  for (genvar j = 0; j < COLS; j++) begin : g_col
    for (genvar s = 0; s < LANES; s++) begin : g_lane
      pe #(.A_W(A_W), .W_W(W_W), .ACC_W(ACC_W)) u_pe (
        .clk   (clk),
        .rst_n (rst_n),
        .en    (en_r),
        .clear (clear_r),
        .a     (a_eff[j][s]),
        .w     (w_r[j]),
        .acc   (acc[j][s])
      );
    end
  end

endmodule
