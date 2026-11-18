// =============================================================================
// tb_pe.sv
// Self-checking testbench for pe. Simulation only: never synthesized.
// Owner: Michael
//
// tb_pe (the top) runs pe_check at three configurations at once:
//   (A_W, W_W, ACC_W) = ( 8,  8, 32)  INT8 x INT8, the accel_pkg defaults
//                       (17,  8, 32)  UINT16 probability (zero-extended) x INT8
//                       (17, 16, 40)  16-bit x 16-bit, the data-by-data case (N6)
// and prints one final line: PASS: N checks, 0 errors / FAIL: E errors in N checks.
//
// pe_check drives a new input every clock, keeps its own running sum (the
// reference), and checks pe's acc against it 3 clocks later. It also:
//   - runs the three largest-magnitude products for as long as the
//     accumulator can hold them (never wraps, N6),
//   - flags any vector whose exact sum would not fit in ACC_W (a test bug),
//   - resets pe in the middle of the run and checks it recovers.
// =============================================================================
`timescale 1ns / 1ps

module pe_check #(
  parameter int A_W   = 8,
  parameter int W_W   = 8,
  parameter int ACC_W = 32,
  parameter int N_CYCLES = 20000    // clocks of input to drive
)(
  input  logic clk,
  output logic done,
  output int   checks,
  output int   errors
);

  localparam int LAT = 3;            // pe's latency, inputs to acc

  // Largest operands at these widths
  localparam longint A_MIN = -(64'sd1 <<< (A_W-1));
  localparam longint A_MAX =  (64'sd1 <<< (A_W-1)) - 1;   // A_W = 17: 65535, UINT16 max
  localparam longint W_MIN = -(64'sd1 <<< (W_W-1));
  localparam longint W_MAX =  (64'sd1 <<< (W_W-1)) - 1;
  localparam longint ACC_MAX = (64'sd1 <<< (ACC_W-1)) - 1;
  localparam longint ACC_MIN = -(64'sd1 <<< (ACC_W-1));

  // How many largest products in a row still fit in ACC_W (at most 300)
  localparam longint P_MAX = A_MIN * W_MIN;                // the largest product magnitude
  localparam int     RUN   = (ACC_MAX / P_MAX > 300) ? 300 : int'(ACC_MAX / P_MAX);
  localparam int     RST_AT = N_CYCLES / 2;                // cycle of the mid-run reset

  // ---- Signals: same names as pe's ports, so `.*` connects them ------------
  logic rst_n = 0;
  logic en    = 0;
  logic clear = 0;
  logic signed [A_W-1:0]   a = '0;
  logic signed [W_W-1:0]   w = '0;
  logic signed [ACC_W-1:0] acc;

  pe #(.A_W(A_W), .W_W(W_W), .ACC_W(ACC_W)) dut (.*);

  // ---- Reference model ------------------------------------------------------
  longint ref_acc = 0;               // exact sum for the latest input (64-bit, cannot wrap)
  longint hist [0:LAT];              // ref_acc over the last few clocks
  int     cyc = 0, since_rst = 0;
  logic   new_en, new_clear;
  longint new_a, new_w;

  initial begin
    foreach (hist[k]) hist[k] = 0;
    checks = 0; errors = 0; done = 0;
  end

  // ---- Driver, reference and checker, all in step with the clock -----------
  always @(posedge clk) begin
    if (!rst_n) begin
      // In reset: pe clears acc and its pipeline, so the reference does too.
      en <= 0; clear <= 0;
      ref_acc = 0;
      foreach (hist[k]) hist[k] = 0;
      since_rst = 0;
    end else begin
      // 1. Check: acc now reflects the input chosen LAT+1 edges ago
      if (since_rst > LAT) begin
        checks++;
        if (acc !== ACC_W'(hist[LAT])) begin
          $display("ERROR (%0d,%0d,%0d) at %0t: acc = %0d, expected %0d",
                   A_W, W_W, ACC_W, $time, acc, hist[LAT]);
          errors++;
        end
      end

      // 2. Age the history by one clock
      for (int k = LAT; k > 0; k--) hist[k] = hist[k-1];

      // 3. Choose this clock's inputs
      if (cyc < RUN) begin                   // largest positive product
        new_en = 1; new_clear = (cyc == 0);       new_a = A_MIN; new_w = W_MIN;
      end else if (cyc < 2*RUN) begin        // largest negative product, a negative
        new_en = 1; new_clear = (cyc == RUN);     new_a = A_MIN; new_w = W_MAX;
      end else if (cyc < 3*RUN) begin        // largest negative product, a positive (UINT16 max at A_W=17)
        new_en = 1; new_clear = (cyc == 2*RUN);   new_a = A_MAX; new_w = W_MIN;
      end else if (cyc < N_CYCLES) begin     // random: gaps, random restarts
        new_en    = (cyc == 3*RUN) || ($urandom_range(0, 9) < 8);   // the restart below must be enabled
        new_clear = (cyc == 3*RUN) || ($urandom_range(0, 63) == 0);  // restart after the edge runs
        new_a     = $signed(A_W'($urandom));
        new_w     = $signed(W_W'($urandom));
      end else begin                         // done: stop feeding
        new_en = 0; new_clear = 0; new_a = 0; new_w = 0;
      end

      en    <= new_en;
      clear <= new_clear;
      a     <= A_W'(new_a);
      w     <= W_W'(new_w);

      // 4. Update the reference with the same inputs
      if (new_en)
        ref_acc = new_clear ? new_a * new_w : ref_acc + new_a * new_w;
      hist[0] = ref_acc;

      // The vectors must never ask pe to wrap (N6). If they do, the test is wrong.
      if (ref_acc > ACC_MAX || ref_acc < ACC_MIN) begin
        $display("ERROR (%0d,%0d,%0d): test vector overflows ACC_W at cycle %0d", A_W, W_W, ACC_W, cyc);
        errors++;
      end

      cyc++;
      since_rst++;
    end
  end

  // ---- Reset, reset again mid-run, then report -------------------------------
  initial begin
    repeat (5) @(posedge clk);
    rst_n <= 1;
    wait (cyc == RST_AT);
    @(posedge clk);
    rst_n <= 0;
    repeat (3) @(posedge clk);
    rst_n <= 1;
    wait (cyc == N_CYCLES + LAT + 2);
    @(posedge clk);
    $display("pe (%0d,%0d,%0d): %0d checks, %0d errors, %0d max-product cycles per sign",
             A_W, W_W, ACC_W, checks, errors, RUN);
    done = 1;
  end

endmodule


module tb_pe;

  logic clk = 0;
  always #5 clk = ~clk;

  logic done [3];
  int   checks [3], errors [3];

  pe_check #(.A_W( 8), .W_W( 8), .ACC_W(32)) c0 (.clk, .done(done[0]), .checks(checks[0]), .errors(errors[0]));
  pe_check #(.A_W(17), .W_W( 8), .ACC_W(32)) c1 (.clk, .done(done[1]), .checks(checks[1]), .errors(errors[1]));
  pe_check #(.A_W(17), .W_W(16), .ACC_W(40)) c2 (.clk, .done(done[2]), .checks(checks[2]), .errors(errors[2]));

  initial begin
    int n, e;
    wait (done[0] && done[1] && done[2]);
    n = checks[0] + checks[1] + checks[2];
    e = errors[0] + errors[1] + errors[2];
    if (e == 0 && checks[0] > 0 && checks[1] > 0 && checks[2] > 0)
      $display("PASS: %0d checks, 0 errors", n);
    else
      $display("FAIL: %0d errors in %0d checks", e, n);
    $finish;
  end

endmodule
