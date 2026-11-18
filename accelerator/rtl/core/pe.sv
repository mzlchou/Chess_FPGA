// =============================================================================
// pe.sv
// Processing element: one multiply-accumulate. acc = acc + a * w.
// Owner:     Michael
// Latency:   3 clock cycles from inputs to acc
// Numerics:  N6 (accumulators never wrap; ACC_W is a parameter, the exporter
//            proves the bound)
// Primitive: one DSP48E2. a_1/w_1 -> A/B regs, prod_1 -> M reg, acc -> P reg.
// Part of:   mac_array -> mme
//
// Parameters. Defaults come from accel_pkg (MAC_A_W, MAC_W_W, MAC_ACC_W), so a normal
// build uses the package values. A testbench or synthesis run may override them per
// instance to build other widths without editing the package.
//   A_W   lane operand width. Signed. An unsigned source is zero-extended by
//         the caller, so UINT16 probabilities use A_W = 17.
//   W_W   column operand width. Signed.
//   ACC_W accumulator width.
// One DSP48E2 holds A_W <= 27 and W_W <= 18 (27 x 18 multiplier), and keeps
// 48 bits of accumulator, so ACC_W <= 48.
// =============================================================================
`timescale 1ns / 1ps

module pe
  import accel_pkg::*;
#(
  parameter int A_W   = MAC_A_W,    // lane operand width (signed)
  parameter int W_W   = MAC_W_W,    // column operand width (signed)
  parameter int ACC_W = MAC_ACC_W   // accumulator width
)(
  input  logic clk,
  input  logic rst_n,

  input  logic en,                        // 1 = use a and w this cycle
  input  logic clear,                     // 1 = start a new sum with this product (only with en)
  input  logic signed [A_W-1:0]   a,      // lane operand (activation, score, probability)
  input  logic signed [W_W-1:0]   w,      // column operand (weight, K word, V word)

  output logic signed [ACC_W-1:0] acc     // running sum
);

  localparam int P_W = A_W + W_W;         // a signed A_W x W_W product fits in A_W + W_W bits

  // Catch configurations that would not fit in one DSP48E2.
  initial begin
    if (A_W > 27 || W_W > 18 || ACC_W > 48 || ACC_W < P_W)
      $error("pe: A_W=%0d W_W=%0d ACC_W=%0d does not fit one DSP48E2 or is narrower than the product",
             A_W, W_W, ACC_W);
  end

  // Pipeline registers
  logic signed [A_W-1:0] a_1;
  logic signed [W_W-1:0] w_1;
  logic                  en_1, clear_1;
  logic signed [P_W-1:0] prod_1;
  logic                  en_2, clear_2;

  // Register the inputs
  // a, w, en, clear  ->  a_1, w_1, en_1, clear_1
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      a_1     <= '0;
      w_1     <= '0;
      en_1    <= 1'b0;
      clear_1 <= 1'b0;
    end else begin
      a_1     <= a;
      w_1     <= w;
      en_1    <= en;
      clear_1 <= clear;
    end
  end

  // Multiply.
  // a_1 * w_1  ->  prod_1   (both signed, so the product is signed, P_W bits)
  // en_1, clear_1  ->  en_2, clear_2
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      prod_1  <= '0;
      en_2    <= 1'b0;
      clear_2 <= 1'b0;
    end else begin
      prod_1  <= a_1 * w_1;
      en_2    <= en_1;
      clear_2 <= clear_1;
    end
  end

  // Accumulate, only when en_2 is 1.
  // clear_2 = 1  ->  acc = prod_1 (start a new sum)
  // clear_2 = 0  ->  acc = acc + prod_1 (keep adding)
  // en_2 = 0     ->  acc holds its value
  // prod_1 is signed, so it is sign-extended to ACC_W before the add.
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      acc <= '0;
    end else if (en_2) begin
      if (clear_2)
        acc <= ACC_W'(prod_1);
      else
        acc <= acc + ACC_W'(prod_1);
    end
  end

endmodule
