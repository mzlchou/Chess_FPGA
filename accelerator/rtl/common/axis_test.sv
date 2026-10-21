// =============================================================================
// axis_test.sv
// Practice module: AXI4-Stream passthrough that adds 1 to every beat.
// Owner:   Michael
// Purpose: learn streams, testbenches and the DMA path before the real design.
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

  // We can accept a new beat when the output register is empty,
  // or when the beat sitting in it is leaving on this clock edge.
  assign s_axis_tready = !m_axis_tvalid || m_axis_tready;

  // The output register: one beat of storage.
  always_ff @(posedge aclk) begin
    if (!aresetn) begin
      m_axis_tvalid <= 1'b0; // start empty
    end else if (s_axis_tvalid && s_axis_tready) begin
      m_axis_tdata  <= s_axis_tdata + 1'b1; // a beat came in: store it, plus 1
      m_axis_tlast  <= s_axis_tlast;
      m_axis_tvalid <= 1'b1;
    end else if (m_axis_tready) begin
      m_axis_tvalid <= 1'b0; // nothing came in, old beat left: empty
    end
  end

endmodule
