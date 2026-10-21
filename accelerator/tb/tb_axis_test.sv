// =============================================================================
// tb_axis_test.sv
// Self-checking testbench for axis_test. Simulation only: never synthesized.
// Sends N_BEATS random beats with random gaps, stalls the output at random,
// and checks every output beat equals its input + 1, in order.
// Owner: Michael
// =============================================================================
`timescale 1ns / 1ps

module tb_axis_test;

  localparam int W       = 64;    // must match the width axis_test is built with
  localparam int N_BEATS = 1000;  // how many beats to send

  // ---- Signals: one per DUT port, same names, so `.*` connects them --------
  logic         aclk = 0;
  logic         aresetn = 0;
  logic [W-1:0] s_axis_tdata = '0;
  logic         s_axis_tvalid = 0;
  logic         s_axis_tready;
  logic         s_axis_tlast = 0;
  logic [W-1:0] m_axis_tdata;
  logic         m_axis_tvalid;
  logic         m_axis_tready = 0;
  logic         m_axis_tlast;

  // ---- Clock and DUT --------------------------------------------------------
  always #5 aclk = ~aclk;                 // 10 ns period = 100 MHz

  axis_test #(.W(W)) dut (.*);

  // ---- Scoreboard state -----------------------------------------------------
  logic [W:0] expected [$];               // queue of {last, data + 1}, oldest first
  logic [W:0] exp_beat;                   // the one being checked
  int sent = 0, received = 0, errors = 0;

  // ---- Driver: sends N_BEATS beats on the input, with random gaps -----------
  initial begin
    repeat (5) @(posedge aclk);
    aresetn <= 1;                         // release reset
    repeat (2) @(posedge aclk);

    for (int i = 0; i < N_BEATS; i++) begin
      s_axis_tvalid <= 0;                         // idle...
      repeat ($urandom_range(0, 3)) @(posedge aclk);  // ...for 0 to 3 cycles
      s_axis_tdata  <= (i % 100 == 0) ? '1 : {$urandom, $urandom};  // all-ones tests wraparound
      s_axis_tlast  <= (i % 16 == 15);            // mark every 16th beat as a packet end
      s_axis_tvalid <= 1;
      do @(posedge aclk); while (!s_axis_tready); // hold the beat until accepted
    end
    s_axis_tvalid <= 0;
  end

  // ---- Sink: the "DMA" on the output, ready about 70% of the time -----------
  always @(posedge aclk)
    m_axis_tready <= ($urandom_range(0, 9) < 7);

  // ---- Input monitor: record what each accepted beat should become ---------
  always @(posedge aclk) begin
    if (aresetn && s_axis_tvalid && s_axis_tready) begin
      expected.push_back({s_axis_tlast, s_axis_tdata + W'(1)});
      sent++;
    end
  end

  // ---- Output monitor: check each beat that leaves --------------------------
  always @(posedge aclk) begin
    if (aresetn && m_axis_tvalid && m_axis_tready) begin
      received++;
      if (expected.size() == 0) begin
        $display("ERROR at %0t: output beat %h with nothing expected", $time, m_axis_tdata);
        errors++;
      end else begin
        exp_beat = expected.pop_front();
        if ({m_axis_tlast, m_axis_tdata} !== exp_beat) begin
          $display("ERROR at %0t: got last=%b data=%h, expected last=%b data=%h",
                   $time, m_axis_tlast, m_axis_tdata, exp_beat[W], exp_beat[W-1:0]);
          errors++;
        end
      end
    end
  end

  // ---- Protocol check making sure nothing changes as DMA nto ready to take --
  logic       was_stalled = 0;
  logic [W:0] stalled_beat;
  always @(posedge aclk) begin
    if (aresetn && was_stalled &&
        (!m_axis_tvalid || {m_axis_tlast, m_axis_tdata} !== stalled_beat)) begin
      $display("ERROR at %0t: output changed while stalled", $time);
      errors++;
    end
    was_stalled  = aresetn && m_axis_tvalid && !m_axis_tready;
    stalled_beat = {m_axis_tlast, m_axis_tdata};
  end

  // ---- Finish: wait for every beat to come out, then report -----------------
  initial begin
    wait (aresetn);
    while (received < N_BEATS) @(posedge aclk);
    repeat (5) @(posedge aclk);
    if (errors == 0 && sent == N_BEATS && received == N_BEATS)
      $display("PASS: %0d beats in, %0d out, 0 errors", sent, received);
    else
      $display("FAIL: %0d errors, %0d sent, %0d received", errors, sent, received);
    $finish;
  end

  // ---- Give up if the design hangs --------------------------------
  initial begin
    #100us;
    $display("FAIL: timeout, %0d sent, %0d received", sent, received);
    $finish;
  end

endmodule
