// =============================================================================
// pe.sv
// Processing element: one multiply-accumulate. acc = acc + a * w.
// Owner:   Michael
// Latency: 3 clock cycles from inputs to acc
// part of mme, mac_array, pe
// =============================================================================
`timescale 1ns / 1ps

module pe
  import accel_pkg::*;
(
  input  logic clk,
  input  logic rst_n,

  input  logic en,      // 1 = use a and w this cycle
  input  logic clear,   // 1 = start a new sum with this product (only with en)
  input  act_t a,       // activation, signed INT8
  input  act_t w,       // weight, signed INT8

  output acc_t acc      // running sum, signed INT32
);

  // Pipeline registers
  act_t a_1, w_1;
  logic en_1, clear_1;
  logic signed [2*DW-1:0] prod_1;
  logic en_2, clear_2;

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
  // a_1 * w_1  ->  prod_1   (INT8 x INT8 fits in 16 signed bits)
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
  always_ff @(posedge clk) begin
    if (!rst_n) begin
      acc <= '0;
    end else if (en_2) begin
      if (clear_2)
        acc <= prod_1;
      else
        acc <= acc + prod_1;
    end
  end

endmodule
