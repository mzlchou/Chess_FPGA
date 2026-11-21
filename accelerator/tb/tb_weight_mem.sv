// =============================================================================
// tb_weight_mem.sv
// Self-checking testbench for weight_mem. Simulation only: never synthesized.
// Owner: Michael
//
// tb_weight_mem runs wm_check at 3 configurations, then prints one line:
// PASS: N checks, 0 errors / FAIL: E errors in N checks.
//
// wm_check: fills the memory through the write port, then alternates
//   - burst blocks: one rd_start, w_ready held at 1. After the first word,
//     a word must come out every cycle (full rate, no bubbles).
//   - random blocks: random w_ready (stalls), random rd_start: restart at an
//     earlier address, restart mid-stream, back-to-back restarts, near the end.
// Every word taken must be mem[start], mem[start+1], ... in order, never past
// the last address. A word that is shown must hold until taken. A mid-run
// reset stops the stream; contents survive.
// =============================================================================
`timescale 1ns / 1ps

module wm_check #(
  parameter int WORD_W   = 64,
  parameter int DEPTH    = 64,
  parameter int RD_LAT   = 1,
  parameter int STYLE    = 0,
  parameter int N_CYCLES = 8000
)(
  input  logic clk,
  output logic done,
  output int   checks,
  output int   errors
);

  localparam int AW     = (DEPTH > 1) ? $clog2(DEPTH) : 1;
  localparam int BLK    = 200;                    // cycles per block
  localparam int T0     = DEPTH;                  // traffic starts after the fill
  localparam int T_END  = T0 + N_CYCLES;
  localparam int RST_AT = T0 + N_CYCLES / 2 + BLK / 2;   // inside a random block

  // ---- DUT ---------------------------------------------------------------------
  logic              rst_n = 0;
  logic              we = 0;
  logic [AW-1:0]     waddr = '0;
  logic [WORD_W-1:0] wdata = '0;
  logic              rd_start = 0;
  logic [AW-1:0]     rd_addr = '0;
  logic              w_valid;
  logic              w_ready = 0;
  logic [WORD_W-1:0] w_data;

  weight_mem #(.WORD_W(WORD_W), .DEPTH(DEPTH), .RD_LAT(RD_LAT), .STYLE(STYLE)) dut (.*);

  // ---- Model -------------------------------------------------------------------
  logic [WORD_W-1:0] mdl [DEPTH];
  logic              active = 0;       // a stream is running
  int                exp_addr = 0;     // address of the next word the stream must give
  int                since_start = 0;
  logic              prev_valid = 0, prev_ready = 0, prev_start = 0;
  logic [WORD_W-1:0] fill_d;
  logic [WORD_W-1:0] prev_data;
  int                cyc = 0, blk, bpos;
  logic              burst;
  logic              n_start, n_ready;
  int                n_addr;
  int                words = 0, restarts = 0;

  function automatic logic [WORD_W-1:0] rand_word();
    logic [WORD_W-1:0] w;
    for (int b = 0; b < WORD_W; b += 32) w[b +: 32] = $urandom;
    return w;
  endfunction

  initial begin checks = 0; errors = 0; done = 0; end

  task automatic err(input string what);
    if (errors < 10)
      $display("ERROR weight_mem D%0d L%0d S%0d at %0t: %s (exp_addr %0d)",
               DEPTH, RD_LAT, STYLE, $time, what, exp_addr);
    errors++;
  endtask

  always @(posedge clk) begin
    if (!rst_n) begin
      active = 0;
      rd_start <= 0; w_ready <= 0; we <= 0;
      prev_valid = 0; prev_ready = 0; prev_start = 0;
    end else begin
      blk   = (cyc - T0) / BLK;
      bpos  = (cyc - T0) % BLK;
      burst = (cyc >= T0) && (blk % 2 == 0);

      // 1. A word taken on this edge must be the next one in the stream
      if (w_valid && w_ready) begin
        checks++;
        if (!active)                     err("word given with no stream running");
        else if (exp_addr >= DEPTH)      err("word given past the last address");
        else if (w_data !== mdl[exp_addr]) err("wrong word");
        exp_addr++;
        words++;
      end

      // 2. A word shown but not taken last edge must still be there (unless that edge restarted)
      if (prev_valid && !prev_ready && !prev_start) begin
        checks++;
        if (!w_valid || w_data !== prev_data) err("word changed or vanished before it was taken");
      end

      // 3. Bursts: after the first word, one word per cycle until the end
      if (burst && active && since_start > RD_LAT + 4 && exp_addr < DEPTH) begin
        checks++;
        if (!w_valid) err("bubble in a full-rate burst");
      end

      // 4. The rd_start the DUT sees on this edge starts the new stream
      if (rd_start) begin
        active = 1; exp_addr = rd_addr; since_start = 0; restarts++;
      end else since_start++;

      prev_valid = w_valid; prev_ready = w_ready; prev_data = w_data; prev_start = rd_start;

      // 5. Choose the next inputs
      n_start = 0; n_addr = 0; n_ready = 0;
      if (cyc < T0) begin                                  // fill
        fill_d = rand_word();
        we <= 1; waddr <= cyc[AW-1:0]; wdata <= fill_d; mdl[cyc] = fill_d;
      end else begin
        we <= 0;
        if (cyc >= T_END) begin
          n_ready = 1;                                     // drain
        end else if (burst) begin
          n_ready = 1;
          if (bpos == 0) begin n_start = 1; n_addr = $urandom_range(0, DEPTH - 1); end
        end else begin
          n_ready = ($urandom_range(0, 9) < 6);
          case ($urandom_range(0, 99))
            0, 1:    begin n_start = 1; n_addr = $urandom_range(0, DEPTH - 1); end                         // anywhere
            2:       begin n_start = 1; n_addr = (exp_addr > 3) ? exp_addr - 3 : 0;                       // earlier
                           if (n_addr > DEPTH - 1) n_addr = DEPTH - 1; end
            3:       begin n_start = 1; n_addr = (DEPTH > 6) ? DEPTH - 1 - $urandom_range(0, 5) : 0; end   // near the end
            4:       begin n_start = 1; n_addr = $urandom_range(0, DEPTH - 1); end                         // back-to-back:
            5:       if (rd_start) begin n_start = 1; n_addr = $urandom_range(0, DEPTH - 1); end           //   only right after one
            default: ;
          endcase
          if (bpos == 0) begin n_start = 1; n_addr = $urandom_range(0, DEPTH - 1); end
        end
      end
      rd_start <= n_start;
      rd_addr  <= n_addr[AW-1:0];
      w_ready  <= n_ready;

      cyc++;
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
    wait (cyc == T_END + RD_LAT + 20);
    @(posedge clk);
    $display("weight_mem D%0d L%0d S%0d: %0d checks, %0d errors (%0d words, %0d restarts)",
             DEPTH, RD_LAT, STYLE, checks, errors, words, restarts);
    done = 1;
  end

endmodule


module tb_weight_mem;

  logic clk = 0;
  always #5 clk = ~clk;

  localparam int N = 3;
  logic done [N];
  int   checks [N], errors [N];

  // small, latency 1, LUTRAM
  wm_check #(.DEPTH(64),   .RD_LAT(1), .STYLE(0)) c0 (.clk, .done(done[0]), .checks(checks[0]), .errors(errors[0]));
  // URAM style, latency 4 (the real setting)
  wm_check #(.DEPTH(512),  .RD_LAT(4), .STYLE(2)) c1 (.clk, .done(done[1]), .checks(checks[1]), .errors(errors[1]));
  // depth not a power of two, latency 3: checks the stop at the last address
  wm_check #(.DEPTH(1000), .RD_LAT(3), .STYLE(1)) c2 (.clk, .done(done[2]), .checks(checks[2]), .errors(errors[2]));

  initial begin
    int n, e;
    bit all_ran;
    wait (done[0] && done[1] && done[2]);
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
