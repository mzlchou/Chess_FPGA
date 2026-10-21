// =============================================================================
// axis_test_wrap.v
// Plain-Verilog wrapper around axis_test, so it can be added to a block design.
// Vivado's block design only accepts Verilog or VHDL at the top of a module
// reference, not SystemVerilog. This file adds no logic: it passes every port
// straight through.
// Owner: Michael
// =============================================================================
`timescale 1ns / 1ps

module axis_test_wrap #(
  parameter W = 64
) (
  input  wire         aclk,
  input  wire         aresetn,

  input  wire [W-1:0] s_axis_tdata,
  input  wire         s_axis_tvalid,
  output wire         s_axis_tready,
  input  wire         s_axis_tlast,

  output wire [W-1:0] m_axis_tdata,
  output wire         m_axis_tvalid,
  input  wire         m_axis_tready,
  output wire         m_axis_tlast
);

  axis_test #(.W(W)) u_axis_test (
    .aclk          (aclk),
    .aresetn       (aresetn),
    .s_axis_tdata  (s_axis_tdata),
    .s_axis_tvalid (s_axis_tvalid),
    .s_axis_tready (s_axis_tready),
    .s_axis_tlast  (s_axis_tlast),
    .m_axis_tdata  (m_axis_tdata),
    .m_axis_tvalid (m_axis_tvalid),
    .m_axis_tready (m_axis_tready),
    .m_axis_tlast  (m_axis_tlast)
  );

endmodule
