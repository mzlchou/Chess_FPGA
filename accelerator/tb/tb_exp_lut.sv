// =============================================================================
// tb_exp_lut.sv
// Self-checking testbench for exp_lut (Softmax exponential lookup table).
// Simulation only: never synthesized.
//
// Verification Coverage:
// 1. Reset behavior (outputs cleared), at start and once mid-run
// 2. Full sweep of all 512 entries [0, 511]
// 3. Clipping behavior for delta >= 512 (clipped to 0x0000)
// 4. Clock enable (en) gating and output holding
// 5. 10,000 random cycles with random enable and delta
//
// Owner: Hoang
// Fixes (Nov 18): check outputs one clock after they update (was a race),
// expected values from the exp formula not the .mem, no back-door ROM load,
// one PASS/FAIL line at the end
// =============================================================================
`timescale 1ns / 1ps

module tb_exp_lut #(
  parameter INIT_FILE = "exp_lut.mem"
);

  localparam int  DEPTH   = 512;
  localparam int  DATA_W  = 16;
  localparam int  DELTA_W = 16;
  localparam int  LAT     = 1;                  // exp_lut latency, delta to val_out
  localparam real S       = 496.0 / 32768.0;    // must match gen_exp_lut.py --scale

  localparam int  N_RAND  = 10000;              // random cycles
  localparam int  P_SWEEP = 0;                  // cycles [0, DEPTH): every entry
  localparam int  P_CLIP  = DEPTH;              // 10 out-of-range values
  localparam int  P_GATE  = P_CLIP + 10;        // 1 lookup, then 3 cycles with en = 0
  localparam int  P_RAND  = P_GATE + 4;         // random stream
  localparam int  P_END   = P_RAND + N_RAND;    // stop feeding
  localparam int  RST_AT  = P_RAND + N_RAND/2;  // mid-run reset

  // ---- Signals matching DUT ports -------------------------------------------
  logic               clk   = 0;
  logic               rst_n = 0;
  logic               en    = 0;
  logic [DELTA_W-1:0] delta = '0;
  logic [DATA_W-1:0]  val_out;
  logic               valid_out;

  always #5 clk = ~clk;    // 100 MHz

  exp_lut #(
    .DEPTH(DEPTH), .DATA_W(DATA_W), .DELTA_W(DELTA_W), .INIT_FILE(INIT_FILE)
  ) dut (
    .clk(clk), .rst_n(rst_n), .en(en), .delta(delta),
    .val_out(val_out), .valid_out(valid_out)
  );

  // ---- Expected value: same formula as gen_exp_lut.py, not read from the .mem --
  function automatic logic [DATA_W-1:0] exp_ref(input int k);
    real    v;
    integer q;
    if (k >= DEPTH) return '0;                  // clipped
    v = $exp(-k * S) * 65535.0;
    q = $rtoi(v + 0.5);                         // round to nearest
    if (q > 65535) q = 65535;
    if (q < 0)     q = 0;
    return q[DATA_W-1:0];
  endfunction

  // The 10 out-of-range deltas of the clip phase
  function automatic int clip_case(input int i);
    case (i)
      0: return DEPTH;      1: return DEPTH + 1;  2: return DEPTH + 8;
      3: return 600;        4: return 1023;       5: return 1024;
      6: return 2048;       7: return 16384;      8: return 32767;
      default: return 65535;
    endcase
  endfunction

  // ---- Model of the DUT outputs, and their history ---------------------------
  logic [DATA_W-1:0] m_val;                    // val_out after the latest input
  logic              m_vld;                    // valid_out after the latest input
  logic [DATA_W-1:0] h_val [0:LAT];
  logic              h_vld [0:LAT];

  int   cyc = 0, since_rst = 0, rst_cycles = 0;
  int   checks = 0, errors = 0;
  logic n_en;
  int   n_delta;

  task automatic model_reset();
    m_val = '0;
    m_vld = 1'b0;
    for (int h = 0; h <= LAT; h++) begin
      h_val[h] = '0;
      h_vld[h] = 1'b0;
    end
  endtask

  initial model_reset();

  always @(posedge clk) begin
    if (!rst_n) begin
      // in reset: outputs should be 0 (skip the first edge, that one applies reset)
      if (rst_cycles > 0) begin
        checks++;
        if (val_out !== '0 || valid_out !== 1'b0) begin
          $display("ERROR at %0t: in reset, val_out = 0x%04h, valid_out = %b (expected 0, 0)",
                   $time, val_out, valid_out);
          errors++;
        end
      end
      rst_cycles++;
      en <= 1'b0;
      model_reset();
      since_rst = 0;
    end else begin
      rst_cycles = 0;

      // 1. Check: outputs now show the input driven LAT+1 edges ago (no race)
      if (since_rst > LAT) begin
        checks++;
        if (valid_out !== h_vld[LAT] || val_out !== h_val[LAT]) begin
          if (errors < 10)
            $display("ERROR at %0t: val_out = 0x%04h valid_out = %b, expected 0x%04h %b",
                     $time, val_out, valid_out, h_val[LAT], h_vld[LAT]);
          errors++;
        end
      end

      // 2. Age the history
      for (int h = LAT; h > 0; h--) begin
        h_val[h] = h_val[h-1];
        h_vld[h] = h_vld[h-1];
      end

      // 3. Choose this clock's input
      if (cyc < P_CLIP) begin                       // every table entry
        n_en = 1'b1; n_delta = cyc - P_SWEEP;
      end else if (cyc < P_GATE) begin              // out of range
        n_en = 1'b1; n_delta = clip_case(cyc - P_CLIP);
      end else if (cyc == P_GATE) begin             // one lookup ...
        n_en = 1'b1; n_delta = 10;
      end else if (cyc < P_RAND) begin              // ... then held with en = 0
        n_en = 1'b0; n_delta = 50;
      end else if (cyc < P_END) begin               // random stream
        n_en    = ($urandom_range(0, 9) < 8);
        n_delta = ($urandom_range(0, 9) < 7) ? $urandom_range(0, DEPTH - 1)
                                             : $urandom_range(DEPTH, 65535);
      end else begin                                // done: stop feeding
        n_en = 1'b0; n_delta = 0;
      end

      en    <= n_en;
      delta <= n_delta[DELTA_W-1:0];

      // 4. Update the model: val_out only changes when en = 1, valid_out follows en
      m_vld = n_en;
      if (n_en) m_val = exp_ref(n_delta);
      h_val[0] = m_val;
      h_vld[0] = m_vld;

      // milestones from the original tb
      if (cyc == 0 || cyc == 1 || cyc == 66 || cyc == DEPTH - 1)
        $display("  Milestone k=%0d: expected 0x%04h", cyc, exp_ref(cyc));

      cyc++;
      since_rst++;
    end
  end

  // ---- Reset, reset again mid-run, then report -------------------------------
  initial begin
    repeat (5) @(posedge clk);
    rst_n <= 1'b1;
    wait (cyc == RST_AT);
    @(posedge clk);
    rst_n <= 1'b0;
    repeat (3) @(posedge clk);
    rst_n <= 1'b1;
    wait (cyc == P_END + LAT + 2);
    @(posedge clk);
    if (errors == 0 && checks > 0)
      $display("PASS: %0d checks, 0 errors", checks);
    else
      $display("FAIL: %0d errors in %0d checks", errors, checks);
    $finish;
  end

endmodule
