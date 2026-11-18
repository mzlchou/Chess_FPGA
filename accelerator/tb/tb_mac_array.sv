// =============================================================================
// tb_mac_array.sv
// Self-checking testbench for mac_array. Simulation only: never synthesized.
// Owner: Michael
//
// tb_mac_array (the top) runs mac_check at four configurations at once:
//   LANES x COLS  (A_W, W_W, ACC_W)  HAS_COL_A
//   4 x 2         ( 8,  8, 32)       0          small, INT8 defaults
//   4 x 2         (17, 16, 40)       1          small, MAC widths, column words
//   64 x 8        ( 8,  8, 32)       0          full size, INT8
//   64 x 8        (17, 16, 40)       1          full size, accel_pkg MAC widths
// and prints one final line: PASS: N checks, 0 errors / FAIL: E errors in N checks.
//
// mac_check drives a new input every clock, keeps a reference sum for every
// (column, lane), and checks every accumulator 4 clocks later, every cycle.
// It also runs:
//   - a wiring test: a[s] = s+1, w[j] = j+1 for one product, so every pe has a
//     different answer and a swapped lane or column shows up,
//   - the three largest-magnitude products on every pe for as long as the
//     accumulator can hold them,
//   - random operands with gaps and restarts, and (HAS_COL_A) a random mix of
//     the shared and per-column lane words,
//   - a reset in mid-run.
// Any test vector whose exact sum would not fit in ACC_W is reported as an error.
// =============================================================================
`timescale 1ns / 1ps

module mac_check #(
  parameter int LANES     = 4,
  parameter int COLS      = 2,
  parameter int A_W       = 8,
  parameter int W_W       = 8,
  parameter int ACC_W     = 32,
  parameter bit HAS_COL_A = 1'b0,
  parameter int N_CYCLES  = 20000
)(
  input  logic clk,
  output logic done,
  output int   checks,
  output int   errors
);

  localparam int LAT = 4;            // mac_array latency, inputs to acc

  localparam longint A_MIN = -(64'sd1 <<< (A_W-1));
  localparam longint A_MAX =  (64'sd1 <<< (A_W-1)) - 1;
  localparam longint W_MIN = -(64'sd1 <<< (W_W-1));
  localparam longint W_MAX =  (64'sd1 <<< (W_W-1)) - 1;
  localparam longint ACC_MAX = (64'sd1 <<< (ACC_W-1)) - 1;
  localparam longint ACC_MIN = -(64'sd1 <<< (ACC_W-1));
  localparam longint P_MAX   = A_MIN * W_MIN;
  localparam int     RUN     = (ACC_MAX / P_MAX > 300) ? 300 : int'(ACC_MAX / P_MAX);
  localparam int     WIRE_AT = 3 * RUN;                    // cycle of the wiring test
  localparam int     RST_AT  = N_CYCLES / 2;

  // ---- DUT ------------------------------------------------------------------
  logic rst_n = 0;
  logic en = 0, clear = 0, col_a_sel = 0;
  // Flat vectors, same bit layout as mac_array's packed ports (Icarus cannot
  // index packed multi-dimensional arrays with loop variables).
  //   a:     lane s           at bits [s*A_W +: A_W]
  //   w:     column j         at bits [j*W_W +: W_W]
  //   a_col: column j, lane s at bits [(j*LANES + s)*A_W +: A_W]
  //   acc:   column j, lane s at bits [(j*LANES + s)*ACC_W +: ACC_W]
  logic [LANES*A_W-1:0]        a     = '0;
  logic [COLS*W_W-1:0]         w     = '0;
  logic [COLS*LANES*A_W-1:0]   a_col = '0;
  logic [COLS*LANES*ACC_W-1:0] acc;

  mac_array #(.LANES(LANES), .COLS(COLS), .A_W(A_W), .W_W(W_W), .ACC_W(ACC_W),
              .HAS_COL_A(HAS_COL_A)) dut (.*);

  // ---- Reference model ------------------------------------------------------
  // Index of (column j, lane s) in the flat arrays below: j*LANES + s
  localparam int NPE = COLS * LANES;
  longint ref_acc [NPE];                  // exact sums for the latest input
  longint hist    [(LAT+1)*NPE];          // ref_acc over the last few clocks: hist[h*NPE + i]
  longint na      [LANES];                // this clock's shared lane word
  longint nac     [NPE];                  // this clock's per-column lane words (0 unless HAS_COL_A)
  longint nw      [COLS];                 // this clock's column operands
  logic signed [ACC_W-1:0] got;
  logic   n_en, n_clear, n_sel;
  longint lane_val;
  int     cyc = 0, since_rst = 0;

  task automatic zero_ref();
    for (int i = 0; i < NPE; i++) begin
      ref_acc[i] = 0;
      for (int h = 0; h <= LAT; h++) hist[h*NPE + i] = 0;
    end
  endtask

  initial begin
    zero_ref();
    foreach (nac[i]) nac[i] = 0;
    checks = 0; errors = 0; done = 0;
  end

  always @(posedge clk) begin
    if (!rst_n) begin
      en <= 0; clear <= 0; col_a_sel <= 0;
      zero_ref();
      since_rst = 0;
    end else if (!done) begin
      // 1. Check every accumulator against the input chosen LAT+1 edges ago
      if (since_rst > LAT) begin
        for (int j = 0; j < COLS; j++)
          for (int s = 0; s < LANES; s++) begin
            checks++;
            got = acc[(j*LANES + s)*ACC_W +: ACC_W];
            if (got !== ACC_W'(hist[LAT*NPE + j*LANES + s])) begin
              if (errors < 10)
                $display("ERROR %0dx%0d (%0d,%0d,%0d) col_a=%0d at %0t: acc[%0d][%0d] = %0d, expected %0d",
                         LANES, COLS, A_W, W_W, ACC_W, HAS_COL_A, $time, j, s,
                         got, hist[LAT*NPE + j*LANES + s]);
              errors++;
            end
          end
      end

      // 2. Age the history
      for (int h = LAT; h > 0; h--)
        for (int i = 0; i < NPE; i++) hist[h*NPE + i] = hist[(h-1)*NPE + i];

      // 3. Choose this clock's inputs
      n_sel = 0;
      if (cyc < RUN) begin                         // largest positive product everywhere
        n_en = 1; n_clear = (cyc == 0);
        foreach (na[s]) na[s] = A_MIN;
        foreach (nw[j]) nw[j] = W_MIN;
      end else if (cyc < 2*RUN) begin              // largest negative, a negative
        n_en = 1; n_clear = (cyc == RUN);
        foreach (na[s]) na[s] = A_MIN;
        foreach (nw[j]) nw[j] = W_MAX;
      end else if (cyc < 3*RUN) begin              // largest negative, a positive
        n_en = 1; n_clear = (cyc == 2*RUN);
        foreach (na[s]) na[s] = A_MAX;
        foreach (nw[j]) nw[j] = W_MIN;
      end else if (cyc == WIRE_AT) begin           // wiring: every pe gets (s+1)(j+1)
        n_en = 1; n_clear = 1;
        foreach (na[s]) na[s] = s + 1;
        foreach (nw[j]) nw[j] = j + 1;
      end else if (cyc < N_CYCLES) begin           // random: gaps, restarts, column words
        n_en    = ($urandom_range(0, 9) < 8);
        n_clear = (cyc == WIRE_AT + 1) || ($urandom_range(0, 63) == 0);
        n_sel   = HAS_COL_A && ($urandom_range(0, 3) == 0);
        foreach (na[s]) na[s] = $signed(A_W'($urandom));
        foreach (nw[j]) nw[j] = $signed(W_W'($urandom));
      end else begin                               // done: stop feeding
        n_en = 0; n_clear = 0;
        foreach (na[s]) na[s] = 0;
        foreach (nw[j]) nw[j] = 0;
      end
      // Per-column lane words: random every cycle, used only when n_sel = 1
      if (HAS_COL_A)
        for (int i = 0; i < NPE; i++)
          nac[i] = $signed(A_W'($urandom));

      en <= n_en; clear <= n_clear; col_a_sel <= n_sel;
      for (int s = 0; s < LANES; s++) a[s*A_W +: A_W] <= A_W'(na[s]);
      for (int j = 0; j < COLS; j++) w[j*W_W +: W_W] <= W_W'(nw[j]);
      for (int i = 0; i < NPE; i++) a_col[i*A_W +: A_W] <= A_W'(nac[i]);

      // 4. Update the reference with the same inputs
      if (n_en)
        for (int j = 0; j < COLS; j++)
          for (int s = 0; s < LANES; s++) begin
            lane_val = n_sel ? nac[j*LANES + s] : na[s];
            ref_acc[j*LANES + s] = n_clear ? lane_val * nw[j]
                                           : ref_acc[j*LANES + s] + lane_val * nw[j];
            if (ref_acc[j*LANES + s] > ACC_MAX || ref_acc[j*LANES + s] < ACC_MIN) begin
              $display("ERROR %0dx%0d: test vector overflows ACC_W at cycle %0d", LANES, COLS, cyc);
              errors++;
            end
          end
      for (int i = 0; i < NPE; i++) hist[i] = ref_acc[i];

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
    $display("mac_array %0dx%0d (%0d,%0d,%0d) col_a=%0d: %0d checks, %0d errors",
             LANES, COLS, A_W, W_W, ACC_W, HAS_COL_A, checks, errors);
    done = 1;
  end

endmodule


module tb_mac_array;

  logic clk = 0;
  always #5 clk = ~clk;

  localparam int N = 4;
  logic done [N];
  int   checks [N], errors [N];

  mac_check #(.LANES( 4), .COLS(2), .A_W( 8), .W_W( 8), .ACC_W(32), .HAS_COL_A(0), .N_CYCLES(20000))
    c0 (.clk, .done(done[0]), .checks(checks[0]), .errors(errors[0]));
  mac_check #(.LANES( 4), .COLS(2), .A_W(17), .W_W(16), .ACC_W(40), .HAS_COL_A(1), .N_CYCLES(20000))
    c1 (.clk, .done(done[1]), .checks(checks[1]), .errors(errors[1]));
  mac_check #(.LANES(64), .COLS(8), .A_W( 8), .W_W( 8), .ACC_W(32), .HAS_COL_A(0), .N_CYCLES(3000))
    c2 (.clk, .done(done[2]), .checks(checks[2]), .errors(errors[2]));
  mac_check #(.LANES(64), .COLS(8), .A_W(17), .W_W(16), .ACC_W(40), .HAS_COL_A(1), .N_CYCLES(3000))
    c3 (.clk, .done(done[3]), .checks(checks[3]), .errors(errors[3]));

  initial begin
    int n, e;
    bit all_ran;
    wait (done[0] && done[1] && done[2] && done[3]);
    n = 0; e = 0; all_ran = 1;
    for (int i = 0; i < N; i++) begin
      n += checks[i];
      e += errors[i];
      if (checks[i] == 0) all_ran = 0;
    end
    if (e == 0 && all_ran)
      $display("PASS: %0d checks, 0 errors", n);
    else
      $display("FAIL: %0d errors in %0d checks", e, n);
    $finish;
  end

endmodule
