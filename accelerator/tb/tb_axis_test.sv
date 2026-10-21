// =============================================================================
// tb_axis_test.sv
// Testbench for axis_test. Simulation only: never synthesized.
// Owner: Michael
// =============================================================================
`timescale 1ns / 1ps

module tb_axis_test;

  localparam int W = 64;  // must match the width axis_test is built with

  // One signal per DUT port, with the same names, so `.*` can connect them
  logic         aclk = 0;
  logic         aresetn;
  logic [W-1:0] s_axis_tdata,  m_axis_tdata;
  logic         s_axis_tvalid, s_axis_tready, s_axis_tlast;
  logic         m_axis_tvalid, m_axis_tready, m_axis_tlast;

  // 10 ns period = 100 MHz
  always #5 aclk = ~aclk;

  // Device under test
  axis_test #(.W(W)) dut (.*);

  initial begin
    // Everything idle, reset held low
    aresetn       = 0;
    s_axis_tdata  = '0;
    s_axis_tvalid = 0;
    s_axis_tlast  = 0;
    m_axis_tready = 0;

    // Release reset after 5 clock edges
    repeat (5) @(posedge aclk);
    aresetn <= 1;

    // TODO (you): driver, sink, scoreboard (see the plan doc)

    repeat (20) @(posedge aclk);
    $display("tb_axis_test: skeleton ran. Next: write the driver, sink and scoreboard.");
    $finish;
  end

endmodule
