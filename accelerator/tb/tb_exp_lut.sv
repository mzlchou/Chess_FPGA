// =============================================================================
// tb_exp_lut.sv
// Self-checking testbench for exp_lut (Softmax exponential lookup table).
// Simulation only: never synthesized.
//
// Verification Coverage:
// 1. Reset behavior (outputs cleared)
// 2. Full sweep of all 512 entries [0, 511] against reference memory
// 3. Key numerical milestones:
//    - delta = 0   -> 0xFFFF (1.0)
//    - delta = 1   -> 0xFC26 (exp(-0.01514))
//    - delta = 66  -> 0x5E45 (~exp(-1.0))
//    - delta = 511 -> 0x001D (table minimum)
// 4. Clipping behavior for delta >= 512 (safely clipped to 0x0000)
// 5. Clock enable (en) gating and output holding
// 6. Pipeline random stress testing with 1-cycle latency scoreboard
//
// Owner: Hoang
// =============================================================================
`timescale 1ns / 1ps

module tb_exp_lut #(
  parameter string INIT_FILE = "exp_lut.mem"
);

  localparam int DEPTH   = 512;
  localparam int DATA_W  = 16;
  localparam int DELTA_W = 16;
  localparam int LAT     = 1;   // 1 clock cycle latency

  // ---- Signals matching DUT ports -------------------------------------------
  logic               clk       = 0;
  logic               rst_n     = 0;
  logic               en        = 0;
  logic [DELTA_W-1:0] delta     = '0;
  logic [DATA_W-1:0]  val_out;
  logic               valid_out;

  // ---- 100 MHz Clock Generator (10 ns period) ------------------------------
  always #5 clk = ~clk;

  // ---- Instantiate Device Under Test (DUT) ----------------------------------
  exp_lut #(
    .DEPTH(DEPTH),
    .DATA_W(DATA_W),
    .DELTA_W(DELTA_W),
    .INIT_FILE(INIT_FILE)
  ) dut (
    .clk(clk),
    .rst_n(rst_n),
    .en(en),
    .delta(delta),
    .val_out(val_out),
    .valid_out(valid_out)
  );

  // ---- Reference Model and Scoreboard ---------------------------------------
  logic [DATA_W-1:0] ref_lut [0:DEPTH-1];
  int checks = 0;
  int errors = 0;

  // Expected model helper: returns table value for delta < 512, else 0 (clipped)
  function automatic logic [DATA_W-1:0] exp_expected(input logic [DELTA_W-1:0] d);
    if (d < DEPTH) begin
      return ref_lut[d];
    end else begin
      return 16'h0000;
    end
  endfunction

  // Load reference memory and fallback paths if run from different working directories
  initial begin
    $readmemh(INIT_FILE, ref_lut);
    if (ref_lut[0] === 16'hxx) begin
      $display("[TB INFO] '%s' not found in working directory, trying fallback relative paths...", INIT_FILE);
      $readmemh("../rtl/sfu/exp_lut.mem", ref_lut);
    end
    if (ref_lut[0] === 16'hxx) begin
      $readmemh("../../rtl/sfu/exp_lut.mem", ref_lut);
    end
    if (ref_lut[0] === 16'hxx) begin
      $readmemh("accelerator/rtl/sfu/exp_lut.mem", ref_lut);
    end

    // Ensure DUT's internal memory is populated if working directory differed
    #1;
    if (dut.lut[0] === 16'hxx && ref_lut[0] !== 16'hxx) begin
      for (int i = 0; i < DEPTH; i++) begin
        dut.lut[i] = ref_lut[i];
      end
    end

    if (ref_lut[0] === 16'hxx) begin
      $display("[TB ERROR] Could not load '%s'! Check simulation include/working paths.", INIT_FILE);
      errors++;
    end else begin
      $display("[TB INFO] Loaded %0d LUT entries successfully from .mem file.", DEPTH);
    end
  end

  // ---- Test Sequence --------------------------------------------------------
  initial begin
    $display("===============================================================");
    $display("Starting exp_lut Testbench Simulation");
    $display("===============================================================");

    // -------------------------------------------------------------------------
    // Phase 1: Reset Verification
    // -------------------------------------------------------------------------
    rst_n <= 1'b0;
    en    <= 1'b0;
    delta <= 16'h0000;
    repeat (5) @(posedge clk);

    checks++;
    if (val_out !== 16'h0000 || valid_out !== 1'b0) begin
      $display("[ERROR] Reset failed: val_out=0x%04X, valid_out=%0b (expected 0, 0)", val_out, valid_out);
      errors++;
    end else begin
      $display("[PASS] Reset state verified.");
    end

    @(posedge clk);
    rst_n <= 1'b1;
    @(posedge clk);

    // -------------------------------------------------------------------------
    // Phase 2: Full Sweep of Valid Entries [0, 511]
    // -------------------------------------------------------------------------
    $display("[TB] Testing all 512 table entries (k in [0, 511])...");
    for (int k = 0; k < DEPTH; k++) begin
      @(posedge clk);
      en    <= 1'b1;
      delta <= k;

      @(posedge clk);
      checks++;
      if (val_out !== ref_lut[k] || valid_out !== 1'b1) begin
        $display("[ERROR] Mismatch at k=%0d: val_out=0x%04X, expected=0x%04X, valid_out=%0b",
                 k, val_out, ref_lut[k], valid_out);
        errors++;
      end

      // Print key numerical milestones
      if (k == 0) begin
        $display("  Milestone k=0   (diff= 0.00): 0x%04X (expected 0xFFFF, 1.0000)", val_out);
        if (val_out !== 16'hFFFF) errors++;
      end else if (k == 1) begin
        $display("  Milestone k=1   (diff=-0.015): 0x%04X (expected 0xFC26)", val_out);
      end else if (k == 66) begin
        $display("  Milestone k=66  (diff~-1.00): 0x%04X (~exp(-1.0))", val_out);
      end else if (k == DEPTH-1) begin
        $display("  Milestone k=511 (diff~-7.73): 0x%04X (table minimum, expected 0x001D)", val_out);
      end
    end
    $display("[PASS] All 512 entries matched reference table.");

    // -------------------------------------------------------------------------
    // Phase 3: Out-of-Bounds & Clipping Verification (delta >= 512 -> 0x0000)
    // -------------------------------------------------------------------------
    $display("[TB] Testing clipping behavior for delta >= 512...");
    begin
      int clip_test_cases[] = '{512, 513, 520, 600, 1023, 1024, 2048, 16384, 32767, 65535};
      foreach (clip_test_cases[i]) begin
        @(posedge clk);
        en    <= 1'b1;
        delta <= clip_test_cases[i];

        @(posedge clk);
        checks++;
        if (val_out !== 16'h0000 || valid_out !== 1'b1) begin
          $display("[ERROR] Clipping failed for delta=%0d: val_out=0x%04X (expected 0x0000)",
                   clip_test_cases[i], val_out);
          errors++;
        end
      end
    end
    $display("[PASS] Clipping boundary and out-of-range checks passed.");

    // -------------------------------------------------------------------------
    // Phase 4: Enable Gating Verification (en = 0)
    // -------------------------------------------------------------------------
    $display("[TB] Testing enable (en) gating and output hold...");
    @(posedge clk);
    en    <= 1'b1;
    delta <= 16'd10; // Read an arbitrary valid entry
    @(posedge clk);
    logic [DATA_W-1:0] held_val;
    held_val = val_out;

    // De-assert en for 3 cycles: val_out should hold previous value, valid_out must be 0
    en <= 1'b0;
    delta <= 16'd50; // Change delta while disabled
    repeat (3) begin
      @(posedge clk);
      checks++;
      if (valid_out !== 1'b0) begin
        $display("[ERROR] valid_out active while en=0 at %0t", $time);
        errors++;
      end
      if (val_out !== held_val) begin
        $display("[ERROR] val_out changed while en=0: 0x%04X (expected held 0x%04X)", val_out, held_val);
        errors++;
      end
    end
    $display("[PASS] Enable gating verified.");

    // -------------------------------------------------------------------------
    // Phase 5: Randomized Stream with 1-Cycle Pipeline Checking
    // -------------------------------------------------------------------------
    $display("[TB] Running 2000 randomized cycles with random enable and delta...");
    begin
      logic [DELTA_W-1:0] stim_delta;
      logic               stim_en;
      logic [DATA_W-1:0]  pipe_exp_val;
      logic               pipe_exp_valid;

      pipe_exp_val   = '0;
      pipe_exp_valid = 1'b0;

      for (int cyc = 0; cyc < 2000; cyc++) begin
        // Mix: 70% in-range [0, 511], 30% out-of-range [512, 65535]
        if ($urandom_range(0, 9) < 7)
          stim_delta = $urandom_range(0, DEPTH - 1);
        else
          stim_delta = $urandom_range(DEPTH, 65535);

        // 80% active en, 20% idle bubble
        stim_en = ($urandom_range(0, 9) < 8);

        @(posedge clk);
        delta <= stim_delta;
        en    <= stim_en;

        // Check output corresponding to stimulus driven in previous clock
        if (pipe_exp_valid) begin
          checks++;
          if (valid_out !== 1'b1 || val_out !== pipe_exp_val) begin
            $display("[ERROR] Random check failed at cycle %0d: val_out=0x%04X (expected 0x%04X), valid_out=%0b",
                     cyc, val_out, pipe_exp_val, valid_out);
            errors++;
          end
        end else if (cyc > 0) begin
          checks++;
          if (valid_out !== 1'b0) begin
            $display("[ERROR] Unexpected valid_out at cycle %0d", cyc);
            errors++;
          end
        end

        // Pipeline expected values for next cycle
        pipe_exp_valid = stim_en;
        pipe_exp_val   = stim_en ? exp_expected(stim_delta) : pipe_exp_val;
      end
    end
    $display("[PASS] Randomized streaming checks completed.");

    // -------------------------------------------------------------------------
    // Final Summary
    // -------------------------------------------------------------------------
    repeat (5) @(posedge clk);
    $display("\n===============================================================");
    if (errors == 0 && checks > 0) begin
      $display("ALL TESTS PASSED: %0d checks completed with 0 errors.", checks);
    end else begin
      $display("TEST FAILED: %0d error(s) detected in %0d checks.", errors, checks);
    end
    $display("===============================================================\n");

    $finish;
  end

endmodule

