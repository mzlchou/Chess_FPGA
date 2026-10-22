// =============================================================================
// tb_pe.sv
// Self-checking testbench for pe. Simulation only: never synthesized.
// Drives a new input every clock, keeps its own running sum (the reference),
// and checks pe's acc against it 3 clocks later.
// Owner: Michael
// =============================================================================
`timescale 1ns / 1ps

module tb_pe;
  import accel_pkg::*;

  localparam int LAT      = 3;       // pe's latency, inputs to acc
  localparam int N_CYCLES = 20000;   // how many clocks of input to drive

  // ---- Signals: same names as pe's ports, so `.*` connects them ------------
  logic clk   = 0;
  logic rst_n = 0;
  logic en    = 0;
  logic clear = 0;
  act_t a     = '0;
  act_t w     = '0;
  acc_t acc;

  // ---- Clock and DUT --------------------------------------------------------
  always #5 clk = ~clk;

  pe dut (.*);

  // ---- Reference model ------------------------------------------------------
  acc_t ref_acc = '0;              // what acc should become for the latest input
  acc_t hist [0:LAT];              // ref_acc over the last few clocks
  int   cyc = 0, checks = 0, errors = 0;
  logic new_en, new_clear;
  act_t new_a, new_w;

  initial foreach (hist[k]) hist[k] = '0;

  // ---- Driver, reference and checker, all in step with the clock -----------
  always @(posedge clk) begin
    if (rst_n) begin
      // 1. Check: acc now reflects the input chosen LAT+1 edges ago
      if (cyc > LAT) begin
        checks++;
        if (acc !== hist[LAT]) begin
          $display("ERROR at %0t: acc = %0d, expected %0d", $time, acc, hist[LAT]);
          errors++;
        end
      end

      // 2. Age the history by one clock
      for (int k = LAT; k > 0; k--) hist[k] = hist[k-1];

      // 3. Choose this clock's inputs
      if (cyc < 300) begin                 // edge case: largest positive product
        new_en = 1; new_clear = (cyc == 0); new_a = -128; new_w = -128;
      end else if (cyc < 600) begin        // edge case: largest negative product
        new_en = 1; new_clear = (cyc == 300); new_a = -128; new_w = 127;
      end else if (cyc < N_CYCLES) begin   // random: gaps, random restarts
        new_en    = ($urandom_range(0, 9) < 8);
        new_clear = ($urandom_range(0, 63) == 0);
        new_a     = $urandom;
        new_w     = $urandom;
      end else begin                       // done: stop feeding
        new_en = 0; new_clear = 0; new_a = 0; new_w = 0;
      end

      en    <= new_en;
      clear <= new_clear;
      a     <= new_a;
      w     <= new_w;

      // 4. Update the reference with the same inputs
      if (new_en)
        ref_acc = new_clear ? acc_t'(new_a * new_w) : ref_acc + acc_t'(new_a * new_w);
      hist[0] = ref_acc;

      cyc++;
    end
  end

  // ---- Reset, then report ---------------------------------------------------
  initial begin
    repeat (5) @(posedge clk);
    rst_n <= 1;
    wait (cyc == N_CYCLES + LAT + 2);
    @(posedge clk);
    if (errors == 0 && checks > 0)
      $display("PASS: %0d checks, 0 errors", checks);
    else
      $display("FAIL: %0d errors in %0d checks", errors, checks);
    $finish;
  end

endmodule
