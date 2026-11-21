// =============================================================================
// tb_mem_bank.sv
// Self-checking testbench for mem_bank. Simulation only: never synthesized.
// Owner: Michael
//
// tb_mem_bank runs mem_check at 4 configurations, then prints one line:
// PASS: N checks, 0 errors / FAIL: E errors in N checks.
//
// mem_check: fills every address first (contents are not reset), then runs
// random reads and writes against a model array. Covers same-address
// read/write (must return the OLD word), both read ports on one address,
// re = 0 holding rdata (checked every cycle), and a mid-run reset (rvalid clears, contents stay).
// =============================================================================
`timescale 1ns / 1ps

module mem_check #(
  parameter int WORD_W   = 16,
  parameter int DEPTH    = 16,
  parameter int N_RD     = 1,
  parameter int RD_LAT   = 1,
  parameter int STYLE    = 0,
  parameter int N_CYCLES = 5000
)(
  input  logic clk,
  output logic done,
  output int   checks,
  output int   errors
);

  localparam int AW     = (DEPTH > 1) ? $clog2(DEPTH) : 1;
  localparam int LAT    = RD_LAT;
  localparam int RST_AT = DEPTH + N_CYCLES / 2;
  localparam int T_END  = DEPTH + N_CYCLES;

  // ---- DUT (flat vectors: Icarus can't index packed 2D arrays with variables)
  logic                   rst_n = 0;
  logic                   we = 0;
  logic [AW-1:0]          waddr = '0;
  logic [WORD_W-1:0]      wdata = '0;
  logic [N_RD-1:0]        re = '0;
  logic [N_RD*AW-1:0]     raddr = '0;
  logic [N_RD*WORD_W-1:0] rdata;
  logic [N_RD-1:0]        rvalid;

  mem_bank #(.WORD_W(WORD_W), .DEPTH(DEPTH), .N_RD(N_RD), .RD_LAT(RD_LAT), .STYLE(STYLE))
    dut (.*);

  // ---- Model -----------------------------------------------------------------
  logic [WORD_W-1:0] mdl [DEPTH];            // what the memory holds
  logic [WORD_W-1:0] m_q [N_RD];             // first read register, per port
  logic [WORD_W-1:0] h_q [LAT+1][N_RD];      // history of m_q
  logic              h_v [LAT+1][N_RD];      // history of re
  logic              h_s [LAT+1][N_RD];      // history of "port has read at least once"
  logic              seen [N_RD];
  logic [WORD_W-1:0] got, n_wdata;
  logic              n_we;
  logic [N_RD-1:0]   n_re;
  int                n_waddr, n_raddr [N_RD];
  int                cyc = 0, since_rst = 0;

  function automatic logic [WORD_W-1:0] rand_word();
    logic [WORD_W-1:0] w;
    for (int b = 0; b < WORD_W; b += 32) w[b +: 32] = $urandom;
    return w;
  endfunction

  initial begin
    checks = 0; errors = 0; done = 0;
    for (int p = 0; p < N_RD; p++) begin
      m_q[p] = '0;
      seen[p] = 1'b0;
      for (int h = 0; h <= LAT; h++) begin h_q[h][p] = '0; h_v[h][p] = 1'b0; h_s[h][p] = 1'b0; end
    end
  end

  always @(posedge clk) begin
    // 1. Check rdata/rvalid against the input chosen LAT+1 edges ago
    if (rst_n && since_rst > LAT && cyc > DEPTH + LAT) begin
      for (int p = 0; p < N_RD; p++) begin
        checks++;
        got = rdata[p*WORD_W +: WORD_W];
        // rdata is checked every cycle once the port has read once (it must hold while re = 0)
        if (rvalid[p] !== h_v[LAT][p] || (h_s[LAT][p] && got !== h_q[LAT][p])) begin
          if (errors < 10)
            $display("ERROR mem_bank W%0d D%0d R%0d L%0d S%0d port %0d at %0t: rvalid=%b rdata=%h, expected %b %h",
                     WORD_W, DEPTH, N_RD, RD_LAT, STYLE, p, $time, rvalid[p], got, h_v[LAT][p], h_q[LAT][p]);
          errors++;
        end
      end
    end

    // 2. Age the history (data registers keep shifting even in reset)
    for (int h = LAT; h > 0; h--)
      for (int p = 0; p < N_RD; p++) begin
        h_q[h][p] = h_q[h-1][p]; h_v[h][p] = h_v[h-1][p]; h_s[h][p] = h_s[h-1][p];
      end

    // 3. Choose this clock's inputs
    n_we = 0; n_re = '0; n_waddr = 0; n_wdata = '0;
    for (int p = 0; p < N_RD; p++) n_raddr[p] = 0;
    if (!rst_n) begin
      // in reset: drive nothing; rdata is undefined until the next read
      for (int p = 0; p < N_RD; p++) seen[p] = 1'b0;
    end else if (cyc < DEPTH) begin            // fill every address once
      n_we = 1; n_waddr = cyc; n_wdata = rand_word();
    end else if (cyc < T_END) begin            // random traffic
      for (int p = 0; p < N_RD; p++) begin
        n_re[p]    = ($urandom_range(0, 9) < 7);
        n_raddr[p] = $urandom_range(0, DEPTH - 1);
      end
      if (N_RD == 2 && $urandom_range(0, 4) == 0) n_raddr[1] = n_raddr[0];   // both ports, one address
      n_we    = ($urandom_range(0, 1) == 1);
      n_waddr = ($urandom_range(0, 3) == 0) ? n_raddr[0] : $urandom_range(0, DEPTH - 1);  // collisions
      n_wdata = rand_word();
    end

    we    <= n_we;
    waddr <= n_waddr[AW-1:0];
    wdata <= n_wdata;
    re    <= n_re;
    for (int p = 0; p < N_RD; p++) raddr[p*AW +: AW] <= n_raddr[p][AW-1:0];

    // 4. Update the model: reads see the memory BEFORE this cycle's write
    for (int p = 0; p < N_RD; p++) begin
      if (n_re[p]) begin m_q[p] = mdl[n_raddr[p]]; seen[p] = 1'b1; end
      h_q[0][p] = m_q[p];
      h_v[0][p] = n_re[p];
      h_s[0][p] = seen[p];
    end
    if (n_we) mdl[n_waddr] = n_wdata;

    if (rst_n) begin cyc++; since_rst++; end
    else since_rst = 0;
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
    wait (cyc == T_END + LAT + 2);
    @(posedge clk);
    $display("mem_bank W%0d D%0d R%0d L%0d S%0d: %0d checks, %0d errors",
             WORD_W, DEPTH, N_RD, RD_LAT, STYLE, checks, errors);
    done = 1;
  end

endmodule


module tb_mem_bank;

  logic clk = 0;
  always #5 clk = ~clk;

  localparam int N = 4;
  logic done [N];
  int   checks [N], errors [N];

  // small LUTRAM, 1 port, latency 1
  mem_check #(.WORD_W(16),   .DEPTH(16),  .N_RD(1), .RD_LAT(1), .STYLE(0)) c0 (.clk, .done(done[0]), .checks(checks[0]), .errors(errors[0]));
  // BRAM, 2 ports, latency 2
  mem_check #(.WORD_W(64),   .DEPTH(32),  .N_RD(2), .RD_LAT(2), .STYLE(1)) c1 (.clk, .done(done[1]), .checks(checks[1]), .errors(errors[1]));
  // real X bank: 64 lanes x 16 bits, 128 deep, LUTRAM, 2 ports
  mem_check #(.WORD_W(1024), .DEPTH(128), .N_RD(2), .RD_LAT(2), .STYLE(0)) c2 (.clk, .done(done[2]), .checks(checks[2]), .errors(errors[2]));
  // URAM-width word, latency 3
  mem_check #(.WORD_W(72),   .DEPTH(64),  .N_RD(1), .RD_LAT(3), .STYLE(2)) c3 (.clk, .done(done[3]), .checks(checks[3]), .errors(errors[3]));

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
