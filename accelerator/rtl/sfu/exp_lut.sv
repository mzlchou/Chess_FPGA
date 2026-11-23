// =============================================================================
// exp_lut.sv
// Look-up table for exponential function exp(-delta * S) used in Softmax.
// Owner:   Hoang
// Latency: 1 clock cycle (synchronous read)
//
// Numerical Specifications (from gen_exp_lut.py):
// - Scale factor: S = 1 / 64 = 0.015625
// - Input:  delta = (x_max - x) >= 0 (integer difference code)
// - Output: Q0.16 unsigned fixed-point (0xFFFF = 1.0, 0x0000 = 0.0)
// - Size:   1024 entries x 16 bits = 2048 bytes (2 KB)
// =============================================================================
`timescale 1ns / 1ps

module exp_lut #(
  parameter int    DEPTH     = 1024,         // Number of LUT entries
  parameter int    ADDR_W    = $clog2(DEPTH) // log_2(1024) = 10 bits
  parameter        INIT_FILE = "exp_lut.mem" // Initialization memory file
) (
  input logic clk,
  input logic rst,
  input logic valid_in,

  // Initial attention-score format signed INT32
  input logic signed [31:0] input_difference,

  // Valid Bits ensures when data_out is ready clock cycle wise
  output logic valid_out,
  output logic [15:0] data_out
);

  // Dedicate the array to be in BRAM rather than LUT
  (* rom_style = "block" *) logic [15:0] rom [0:DEPTH-1];

  // Read .mem file created from python script
  initial begin
    $readmemh(INIT_FILE, rom);
  end

  logic [ADDR_W-1:0] rom_addr_d;
  logic              underflow_d;

  // Safely clamps the 32-bit signed input down to a valid 10-bit ROM address
  always_comb begin
    if (diff_in <= 32'sd0) begin // Saturate to 1.0
            rom_addr_d  = '0;               
            underflow_d = 1'b0;
        end else if (diff_in >= DEPTH) begin // Underflow 
            rom_addr_d  = '0;
            underflow_d = 1'b1;             
        end else begin
            rom_addr_d  = diff_in[ADDR_W-1:0]; // Direct Memory read
            underflow_d = 1'b0;
        end
  end

  // Reads
  always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_out <= 1'b0;
            data_out  <= 16'h0000;
        end else begin
            valid_out <= valid_in;
            data_out  <= underflow_d ? 16'h0000 : rom[rom_addr_d];
        end
    end

endmodule

