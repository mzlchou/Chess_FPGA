// =============================================================================
// tb_mme.sv
// Self-checking testbench for mme. Simulation only: never synthesized.
// Owner: Michael
//
// tb_mme runs mme_check at 3 configurations, then prints one line:
// PASS: N checks, 0 errors / FAIL: E errors in N checks.
//
// mme_check puts the real memories around mme: mem_bank for the lane bank (X, Q),
// the column bank (K) and the param bank (bias), and weight_mem for the weights.
// It fills them with random words (plus the extreme values -32768, 32767, -128,
// 127), then runs random AXW and AXA_QK commands back to back:
//   - random sizes, including 1 step, 1 column and a part-full last pass,
//   - bias on or off,
//   - random stalls on the weight stream and on d_ready, or full rate.
// Every beat taken is checked against a reference sum computed here: column
// number, d_last, all lanes. A beat shown and not taken must hold. done must
// come once, after the last beat, and row_max must be the max of every beat.
// A reset in the middle of a command throws that command away; the memories
// keep their contents and the next commands must still be right.
// NEEDS TO BE RUN WITH --O0 IN XSIM OR CRASHES
// =============================================================================
`timescale 1ns / 1ps

module mme_check
  import accel_pkg::*;
#(
  parameter int LANES  = 8,
  parameter int COLS   = 4,
  parameter int A_LAT  = 1,
  parameter int P_LAT  = 1,
  parameter int W_LAT  = 1,
  parameter int N_CMDS = 200
)(
  input  logic clk,
  output logic done,
  output int   checks,
  output int   errors
);

  localparam int ACT_W = 16, WT_W = 8, BIAS_W = 32, ACC_W = 40, ADDR_W = 16, N_W = 12;
  localparam int AD  = 64;                       // lane and column bank depth
  localparam int WD  = 512;                      // weight words
  localparam int PD  = 16;                       // param words
  localparam int AAW = 6, WAW = 9, PAW = 4;
  localparam int T0  = WD;                       // commands start after the fill
  localparam int LAND_N = A_LAT + 3;

  // ---- DUT and memories ---------------------------------------------------------
  logic rst_n = 0;

  logic                   start = 0;
  logic [1:0]             mode = 0;
  logic [N_W-1:0]         n_steps = 1, n_cols = 1;
  logic [ADDR_W-1:0]      a_base = 0, c_base = 0, p_base = 0;
  logic                   bias_en = 0;
  logic                   busy, mme_done;

  logic                   a_re, c_re, p_re;
  logic [ADDR_W-1:0]      a_raddr, c_raddr, p_raddr;
  logic [LANES*ACT_W-1:0] a_rdata, c_rdata;
  logic [COLS*BIAS_W-1:0] p_rdata;

  logic                   w_rd_start, w_valid, w_ready, wm_valid, wm_ready;
  logic [ADDR_W-1:0]      w_rd_addr;
  logic [COLS*WT_W-1:0]   w_data;
  logic                   gate = 0;              // stalls the weight stream between weight_mem and mme

  logic                   d_valid, d_last;
  logic                   d_ready = 0;
  logic [LANES*ACC_W-1:0] d_data, row_max;
  logic [N_W-1:0]         d_col;

  logic                   we = 0, wwe = 0, pwe = 0;
  logic [AAW-1:0]         waddr = 0;
  logic [WAW-1:0]         wwaddr = 0;
  logic [PAW-1:0]         pwaddr = 0;
  logic [LANES*ACT_W-1:0] awdata = 0, cwdata = 0;
  logic [COLS*WT_W-1:0]   wwdata = 0;
  logic [COLS*BIAS_W-1:0] pwdata = 0;

  mme #(.LANES(LANES), .COLS(COLS), .A_LAT(A_LAT), .P_LAT(P_LAT)) dut (
    .clk, .rst_n,
    .start, .mode, .n_steps, .n_cols, .a_base, .c_base, .p_base, .bias_en,
    .busy, .done(mme_done),
    .a_re, .a_raddr, .a_rdata,
    .c_re, .c_raddr, .c_rdata,
    .w_rd_start, .w_rd_addr, .w_valid, .w_ready, .w_data,
    .p_re, .p_raddr, .p_rdata,
    .d_valid, .d_ready, .d_data, .d_col, .d_last,
    .row_max
  );

  mem_bank #(.WORD_W(LANES*ACT_W), .DEPTH(AD), .N_RD(1), .RD_LAT(A_LAT), .STYLE(0)) u_abank (
    .clk, .rst_n, .we(we), .waddr(waddr), .wdata(awdata),
    .re(a_re), .raddr(a_raddr[AAW-1:0]), .rdata(a_rdata), .rvalid());

  mem_bank #(.WORD_W(LANES*ACT_W), .DEPTH(AD), .N_RD(1), .RD_LAT(A_LAT), .STYLE(0)) u_cbank (
    .clk, .rst_n, .we(we), .waddr(waddr), .wdata(cwdata),
    .re(c_re), .raddr(c_raddr[AAW-1:0]), .rdata(c_rdata), .rvalid());

  mem_bank #(.WORD_W(COLS*BIAS_W), .DEPTH(PD), .N_RD(1), .RD_LAT(P_LAT), .STYLE(0)) u_pbank (
    .clk, .rst_n, .we(pwe), .waddr(pwaddr), .wdata(pwdata),
    .re(p_re), .raddr(p_raddr[PAW-1:0]), .rdata(p_rdata), .rvalid());

  weight_mem #(.WORD_W(COLS*WT_W), .DEPTH(WD), .RD_LAT(W_LAT), .STYLE(0)) u_wmem (
    .clk, .rst_n, .we(wwe), .waddr(wwaddr), .wdata(wwdata),
    .rd_start(w_rd_start), .rd_addr(w_rd_addr[WAW-1:0]),
    .w_valid(wm_valid), .w_ready(wm_ready), .w_data(w_data));

  assign w_valid  = wm_valid && gate;
  assign wm_ready = w_ready && gate;

  // ---- Model ----------------------------------------------------------------------
  logic [LANES*ACT_W-1:0] am [AD];               // lane bank (X, Q)
  logic [LANES*ACT_W-1:0] cm [AD];               // column bank (K)
  logic [COLS*WT_W-1:0]   wm [WD];               // weights
  logic [COLS*BIAS_W-1:0] pm [PD];               // biases

  function automatic logic [LANES*ACT_W-1:0] rand_act();
    logic [LANES*ACT_W-1:0] w;
    logic [31:0] r;
    for (int s = 0; s < LANES; s++) begin
      r = $urandom;
      case ($urandom_range(0, 19))
        0:       w[s*ACT_W +: ACT_W] = 16'h8000;
        1:       w[s*ACT_W +: ACT_W] = 16'h7FFF;
        default: w[s*ACT_W +: ACT_W] = r[ACT_W-1:0];
      endcase
    end
    return w;
  endfunction

  function automatic logic [COLS*WT_W-1:0] rand_wt();
    logic [COLS*WT_W-1:0] w;
    logic [31:0] r;
    for (int j = 0; j < COLS; j++) begin
      r = $urandom;
      case ($urandom_range(0, 19))
        0:       w[j*WT_W +: WT_W] = 8'h80;
        1:       w[j*WT_W +: WT_W] = 8'h7F;
        default: w[j*WT_W +: WT_W] = r[WT_W-1:0];
      endcase
    end
    return w;
  endfunction

  function automatic logic [COLS*BIAS_W-1:0] rand_bias();
    logic [COLS*BIAS_W-1:0] w;
    for (int j = 0; j < COLS; j++) w[j*BIAS_W +: BIAS_W] = $urandom;
    return w;
  endfunction

  function automatic longint act(input logic [LANES*ACT_W-1:0] w, input int s);
    logic signed [ACT_W-1:0] v;
    longint r;
    v = w[s*ACT_W +: ACT_W];
    r = v;
    return r;
  endfunction

  function automatic longint wt(input logic [COLS*WT_W-1:0] w, input int j);
    logic signed [WT_W-1:0] v;
    longint r;
    v = w[j*WT_W +: WT_W];
    r = v;
    return r;
  endfunction

  function automatic longint bs(input logic [COLS*BIAS_W-1:0] w, input int j);
    logic signed [BIAS_W-1:0] v;
    longint r;
    v = w[j*BIAS_W +: BIAS_W];
    r = v;
    return r;
  endfunction

  function automatic longint lane40(input logic [LANES*ACC_W-1:0] w, input int s);
    logic signed [ACC_W-1:0] v;
    longint r;
    v = w[s*ACC_W +: ACC_W];
    r = v;
    return r;
  endfunction

  // the command running now
  logic   active = 0;
  int     c_mode, c_ns, c_nc, c_a, c_c, c_p, exp_col;
  bit     c_bias, c_fr;
  longint rmax [LANES];

  // expected value of column c, lane s
  function automatic longint expv(input int c, input int s);
    int p, j;
    longint sum;
    p = c / COLS;
    j = c % COLS;
    sum = 0;
    for (int k = 0; k < c_ns; k++)
      if (c_mode == MODE_AXW) sum += act(am[c_a + k], s) * wt(wm[c_c + p*c_ns + k], j);
      else                    sum += act(am[c_a + k], s) * act(cm[c_c + k], c);
    if (c_bias) sum += bs(pm[c_p + p], j);
    return sum;
  endfunction

  // ---- Driver and checker (one clocked block, so nothing races) -------------------
  int     cyc = 0, idle = 0, gap = 0, issued = 0, finished_cmds = 0, aborted = 0;
  int     beats = 0, n_axw = 0, n_qk = 0, t_start = 0, perf_cyc = 0, perf_ideal = 0;
  logic   prev_dv = 0, prev_dr = 0, rst_req = 0, all_done = 0;
  logic [LANES*ACC_W-1:0] prev_data;
  logic [N_W-1:0]         prev_col;
  logic                   prev_last;
  longint e, g;
  int     n_pass, n_st, n_cl, max_st, max_cl, dcol_i;
  logic   last_e;
  bit     ok;

  initial begin checks = 0; errors = 0; done = 0; end

  task automatic err(input string what);
    if (errors < 10)
      $display("ERROR mme L%0d C%0d A%0d P%0d W%0d at %0t: %s (cmd %0d mode %0d K %0d N %0d col %0d)",
               LANES, COLS, A_LAT, P_LAT, W_LAT, $time, what, issued, c_mode, c_ns, c_nc, exp_col);
    errors++;
  endtask

  always @(posedge clk) begin
    if (!rst_n) begin
      if (active) aborted++;
      active = 0;
      start <= 0; d_ready <= 0; gate <= 0;
      prev_dv = 0; prev_dr = 0;
    end else begin

      // 1. A beat taken on this edge must be the next column, right in every lane
      if (d_valid && d_ready) begin
        checks++;
        beats++;
        idle = 0;
        if (!active) err("beat with no command running");
        else if (exp_col >= c_nc) err("more beats than columns");
        else begin
          dcol_i = d_col;
          last_e = (exp_col == c_nc - 1);
          if (dcol_i != exp_col)  err("wrong d_col");
          if (d_last !== last_e)  err("wrong d_last");
          ok = 1;
          for (int s = 0; s < LANES; s++) begin
            e = expv(exp_col, s);
            g = lane40(d_data, s);
            if (g != e) ok = 0;
            if (exp_col == 0 || e > rmax[s]) rmax[s] = e;
          end
          if (!ok) err("wrong d_data");
          exp_col++;
        end
      end

      // 2. A beat shown and not taken must hold
      if (prev_dv && !prev_dr) begin
        checks++;
        if (!d_valid || d_data !== prev_data || d_col !== prev_col || d_last !== prev_last)
          err("beat changed or vanished before it was taken");
      end
      prev_dv = d_valid; prev_dr = d_ready; prev_data = d_data; prev_col = d_col; prev_last = d_last;

      // 3. done: once, after the last beat, with the right row_max
      if (mme_done) begin
        checks++;
        if (!active)               err("done with no command running");
        else if (exp_col != c_nc)  err("done before every column came out");
        else begin
          ok = 1;
          for (int s = 0; s < LANES; s++) if (lane40(row_max, s) != rmax[s]) ok = 0;
          if (!ok) err("wrong row_max");
          if (c_fr) perf_cyc = cyc - t_start;
        end
        active = 0;
        finished_cmds++;
      end
      if (active) idle++;
      if (idle > 3000) begin err("hung"); active = 0; idle = 0; end

      // 4. Mid-run reset, inside a command that already gave a beat
      if (finished_cmds == N_CMDS / 2 && active && exp_col >= 1 && !rst_req) rst_req = 1;

      // 5. Next inputs
      start <= 0;
      if (cyc < T0) begin                                    // fill
        we  <= (cyc < AD); waddr  <= cyc[AAW-1:0];
        wwe <= 1;          wwaddr <= cyc[WAW-1:0];
        pwe <= (cyc < PD); pwaddr <= cyc[PAW-1:0];
        if (cyc < AD) begin am[cyc] = rand_act(); cm[cyc] = rand_act(); awdata <= am[cyc]; cwdata <= cm[cyc]; end
        wm[cyc] = rand_wt(); wwdata <= wm[cyc];
        if (cyc < PD) begin pm[cyc] = rand_bias(); pwdata <= pm[cyc]; end
      end else begin
        we <= 0; wwe <= 0; pwe <= 0;
        if (!active && !busy && !start && !mme_done && issued <= N_CMDS) begin
          if (gap > 0) gap--;
          else begin
            // pick a command
            if (issued == N_CMDS) begin                      // last one: full rate, for the cycle count
              c_mode = MODE_AXW; n_st = 40; n_cl = 3 * COLS; c_fr = 1;
            end else if (issued < 4) begin                   // smallest cases first
              if (issued % 2 == 1) c_mode = MODE_AXA_QK; else c_mode = MODE_AXW;
              n_st = 1 + issued / 2; n_cl = 1; c_fr = 1;
            end else begin
              if ($urandom_range(0, 1) == 0) begin c_mode = MODE_AXW;    max_st = 24; max_cl = 3*COLS + 3; end
              else                           begin c_mode = MODE_AXA_QK; max_st = 40; max_cl = LANES;      end
              n_st = $urandom_range(1, max_st);
              n_cl = $urandom_range(1, max_cl);
              c_fr = ($urandom_range(0, 3) == 0);
            end
            n_pass = (n_cl + COLS - 1) / COLS;
            c_ns   = n_st; c_nc = n_cl;
            c_a    = $urandom_range(0, AD - n_st);
            if (c_mode == MODE_AXW) c_c = $urandom_range(0, WD - n_pass*n_st);
            else                    c_c = $urandom_range(0, AD - n_st);
            c_p    = $urandom_range(0, PD - n_pass);
            c_bias = $urandom_range(0, 1);
            if (issued == N_CMDS) c_bias = 0;
            start   <= 1;
            mode    <= c_mode;
            n_steps <= c_ns;
            n_cols  <= c_nc;
            a_base  <= c_a;
            c_base  <= c_c;
            p_base  <= c_p;
            bias_en <= c_bias;
            active = 1; exp_col = 0; idle = 0; t_start = cyc;
            if (c_mode == MODE_AXW) n_axw++; else n_qk++;
            if (issued == N_CMDS) perf_ideal = n_pass * n_st;
            issued++;
            gap = 0;
            if ($urandom_range(0, 2) != 0) gap = $urandom_range(1, 3);
          end
        end
        if (active && c_fr) begin d_ready <= 1; gate <= 1; end
        else begin
          d_ready <= ($urandom_range(0, 9) < 6);
          gate    <= ($urandom_range(0, 9) < 7);
        end
      end

      if (issued > N_CMDS && !active && !all_done) all_done = 1;
      cyc++;
      if (cyc > T0 + N_CMDS * 3000) begin
        if (!all_done) err("ran out of time");
        all_done = 1;
      end
    end
  end

  // ---- Reset, reset again inside a command, then report -----------------------------
  initial begin
    repeat (5) @(posedge clk);
    rst_n <= 1;
    wait (rst_req);
    @(posedge clk);
    rst_n <= 0;
    repeat (3) @(posedge clk);
    rst_n <= 1;
  end

  initial begin
    wait (all_done);
    repeat (5) @(posedge clk);
    if (aborted != 1) begin
      $display("ERROR mme L%0d C%0d: mid-run reset did not happen inside a command", LANES, COLS);
      errors++;
    end
    $display("mme L%0d C%0d A%0d P%0d W%0d: %0d checks, %0d errors (%0d AXW, %0d AXA_QK, %0d beats); last AXW K=%0d N=%0d full rate: %0d cycles, %0d steps",
             LANES, COLS, A_LAT, P_LAT, W_LAT, checks, errors, n_axw, n_qk, beats, c_ns, c_nc, perf_cyc, perf_ideal);
    done = 1;
  end

endmodule


module tb_mme;

  logic clk = 0;
  always #5 clk = ~clk;

  localparam int N = 3;
  logic done [N];
  int   checks [N], errors [N];

  // small grid, every latency 1
  mme_check #(.LANES(8),  .COLS(4), .A_LAT(1), .P_LAT(1), .W_LAT(1), .N_CMDS(400)) c0 (.clk, .done(done[0]), .checks(checks[0]), .errors(errors[0]));
  // small grid, mixed latencies (weight_mem at the URAM setting)
  mme_check #(.LANES(8),  .COLS(4), .A_LAT(2), .P_LAT(3), .W_LAT(4), .N_CMDS(400)) c1 (.clk, .done(done[1]), .checks(checks[1]), .errors(errors[1]));
  // full size 64 x 8
  mme_check #(.LANES(64), .COLS(8), .A_LAT(2), .P_LAT(2), .W_LAT(4), .N_CMDS(150)) c2 (.clk, .done(done[2]), .checks(checks[2]), .errors(errors[2]));

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
