// =============================================================================
// axis_test.sv
// Practice module: AXI4-Stream passthrough that adds 1 to every beat.
// Owner:   Michael
// Purpose: to learn streams and the DMA path before the real design.
// Latency: 1 clock cycle
// =============================================================================
`timescale 1ns / 1ps

module axis_test #(
  parameter int W = 64 // stream width in bits; the DMA uses 64
) (
  input  logic         aclk,
  input  logic         aresetn,

  // Input stream: from the DMA (MM2S)
  input  logic [W-1:0] s_axis_tdata,
  input  logic         s_axis_tvalid,
  output logic         s_axis_tready,
  input  logic         s_axis_tlast,

  // Output stream: to the DMA (S2MM)
  output logic [W-1:0] m_axis_tdata,
  output logic         m_axis_tvalid,
  input  logic         m_axis_tready,
  output logic         m_axis_tlast
);

  // TODO: a one register pipeline stage.
  //
  // s_axis_tready: we can take a new beat when the output register is empty,
  //                or when its current beat is leaving this cycle.
  //
  // always_ff @(posedge aclk):
  //   on reset          -> clear m_axis_tvalid (data registers can be left alone)
  //   beat accepted     -> capture s_axis_tdata + 1 and s_axis_tlast, set valid
  //   beat leaves and
  //   nothing new comes -> clear valid

endmodule
